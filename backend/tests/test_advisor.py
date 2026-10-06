"""AI Advisor: estrazione, domande mirate, motori deterministici, spiegazioni verificate, privacy."""

import json

from app.ai.advisor_llm import extraction_schema, find_budget, grounded
from app.ai.base import LLMError
from app.services.advisor import TARGET_QID

from .conftest import make_advisor, run


class ScriptedLLM:
    """LLM finto: restituisce in ordine le risposte preparate (stringhe) o solleva eccezioni."""

    name = "scripted"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    async def complete(self, messages, *, json_schema=None):
        self.calls.append({"schema": json_schema is not None, "messages": [m.content for m in messages]})
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def converse(adv, *steps):
    turn = run(adv.start())
    sid = turn.session.session_id
    for st in steps:
        turn = run(adv.message(sid, quick_reply=st)) if isinstance(st, tuple) else run(adv.message(sid, st))
    return turn


# ------------------------------------------------------------------ estrazione
def test_budget_parsing():
    assert find_budget("Ho 400 euro") == 400
    assert find_budget("budget di 1.200 €") == 1200
    assert find_budget("posso spendere al massimo 250") == 250
    assert find_budget("€ 99") == 99
    assert find_budget("voglio fare trekking") is None


def test_kit_request_asks_only_missing_info():
    _, adv = make_advisor()
    t = converse(adv, "Ho 400 euro, voglio iniziare a fare trekking e non ho praticamente nulla.")
    assert t.target.key == "configurator:kit-trekking"
    assert t.session.state.pending_question == "use"  # una sola domanda
    assert {q.question_id for q in t.quick_replies} == {"use"}
    assert "Fino a 400 €" in t.understood and "Principiante" in t.understood


def test_full_kit_flow_respects_budget():
    repos, adv = make_advisor()
    t = converse(adv, "Ho 400 euro, voglio iniziare a fare trekking e non ho praticamente nulla.", ("use", "day_hike"))
    assert t.config_session_id
    cs = run(repos.config_sessions.get(t.config_session_id))
    assert cs.result.total_for_ranking <= 400
    assert cs.answers["experience"] == "beginner" and cs.answers["use"] == "day_hike"


def test_finder_flow_and_budget_change():
    repos, adv = make_advisor()
    t = converse(adv, "Cerco scarpe da trekking per escursioni in giornata, budget 120 euro")
    assert t.finder_session_id
    s1 = run(repos.sessions.get(t.finder_session_id))
    assert s1.result.profile.budget_max == 120
    t2 = run(adv.message(t.session.session_id, "anzi, posso arrivare a 250 euro"))
    s2 = run(repos.sessions.get(t2.finder_session_id))
    assert s2.result.profile.budget_max == 250


def test_budget_too_low_for_kit_suggests_minimum():
    _, adv = make_advisor()
    t = converse(adv, "Mi serve tutto il necessario per trekking di più giorni, ho 120 euro")
    assert "servono almeno" in t.text
    assert all(q.question_id == "budget" and q.value > 120 for q in t.quick_replies)


def test_off_topic_and_unknown_target():
    _, adv = make_advisor()
    t = converse(adv, "che tempo fa domani a Milano?")
    assert t.session.state.pending_question == TARGET_QID
    assert {q.question_id for q in t.quick_replies} == {TARGET_QID}
    t2 = run(adv.message(t.session.session_id, quick_reply=(TARGET_QID, "finder:scarpe-trekking")))
    assert t2.session.state.target == "finder:scarpe-trekking"


def test_session_does_not_store_user_text():
    repos, adv = make_advisor()
    secret = "Mi chiamo Mario Rossi e abito in via Roma 1, ho 400 euro per fare trekking"
    t = converse(adv, secret)
    stored = run(repos.advisor_sessions.get(t.session.session_id)).model_dump_json()
    assert "Mario" not in stored and "via Roma" not in stored


# ------------------------------------------------------------- LLM (scriptato)
def test_llm_extraction_is_validated():
    bad_value = json.dumps({"target": "configurator:kit-trekking", "off_topic": False,
                            "answers": {"use": "volare", "budget": 500, "experience": "expert", "inventato": 1}})
    llm = ScriptedLLM(bad_value, "Ecco il tuo kit, pensato per te.")
    repos, adv = make_advisor(llm)
    t = converse(adv, "qualsiasi cosa")
    # "volare" non è un valore ammesso -> scartato -> l'advisor chiede l'uso
    assert t.session.state.pending_question == "use"
    assert "inventato" not in t.session.state.answers
    assert llm.calls[0]["schema"] is True


def test_llm_failure_falls_back_to_rules():
    llm = ScriptedLLM(LLMError("timeout"), LLMError("down"))
    _, adv = make_advisor(llm)
    t = converse(adv, "Cerco scarpe da trekking per escursioni in giornata, budget 120 euro")
    assert t.finder_session_id  # le regole hanno capito tutto
    assert t.text_source == "template"


def test_explanation_with_invented_price_is_rejected():
    extraction = json.dumps({"target": "finder:scarpe-trekking", "off_topic": False,
                             "answers": {"use": "day_hike", "budget": 120}})
    llm = ScriptedLLM(extraction, "Ti consiglio questa scarpa, costa solo 19,99 € ed è perfetta.")
    _, adv = make_advisor(llm)
    t = converse(adv, "scarpe per escursioni, 120 euro")
    assert t.text_source == "template"
    assert "19,99" not in t.text


def test_grounded_explanation_is_used():
    extraction = json.dumps({"target": "finder:scarpe-trekking", "off_topic": False,
                             "answers": {"use": "day_hike", "budget": 120}})
    llm = ScriptedLLM(extraction, "Per le tue escursioni ti consiglio la prima proposta: è comoda e rientra nel budget di 120 €.")
    _, adv = make_advisor(llm)
    t = converse(adv, "scarpe per escursioni, 120 euro")
    assert t.text_source == "llm"


def test_grounded_check():
    payload = {"budget": 300, "prodotti": [{"prezzo_attuale": 116.72}]}
    assert grounded("Costa 116,72 € e resti entro 300 euro", payload)
    assert not grounded("Costa 89 €", payload)


def test_schema_contains_all_questions():
    _, adv = make_advisor()
    targets = run(adv.targets())
    schema = extraction_schema(targets)
    props = schema["properties"]["answers"]["properties"]
    assert {"use", "experience", "weather", "budget", "crampons", "wide"} <= set(props)
    assert schema["properties"]["answers"]["required"] == list(props)  # richiesto da OpenAI strict


def test_reproducible_with_rules():
    _, a1 = make_advisor()
    _, a2 = make_advisor()
    msg = "Ho 600 euro per l'attrezzatura per trekking di più giorni, sono esperto"
    r1, r2 = converse(a1, msg), converse(a2, msg)
    assert r1.text == r2.text


def test_invalid_json_from_llm_falls_back_to_rules():
    llm = ScriptedLLM("{non json", LLMError("down"))
    _, adv = make_advisor(llm)
    t = converse(adv, "Cerco scarpe da trekking per escursioni in giornata, budget 120 euro")
    assert t.finder_session_id
