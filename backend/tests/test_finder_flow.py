import pytest

from app.scoring import flow
from app.seed import trekking
from app.services.finder import Incomplete

from .conftest import make_services, run

F = trekking.finder_definition()


def test_conditional_questions():
    assert "ankle" not in [q.id for q in flow.visible_questions(F, {"use": "walk"})]
    assert "ankle" in [q.id for q in flow.visible_questions(F, {"use": "day_hike"})]
    assert "crampons" in [q.id for q in flow.visible_questions(F, {"use": "alpine"})]


def test_prune_when_answer_changes():
    answers = {"use": "day_hike", "ankle": "mid"}
    answers["use"] = "walk"
    assert flow.prune_answers(F, answers) == {"use": "walk"}


def test_validation():
    q = {x.id: x for x in F.questions}
    with pytest.raises(flow.InvalidAnswer):
        flow.validate_answer(q["use"], "volare")
    with pytest.raises(flow.InvalidAnswer):
        flow.validate_answer(q["priorities"], ["comfort", "grip", "durability"])
    with pytest.raises(flow.InvalidAnswer):
        flow.validate_answer(q["budget"], 10000)
    assert flow.validate_answer(q["budget"], "120") == 120.0


def test_full_session_and_edit():
    _, _, _, svc = make_services()
    st = run(svc.start("scarpe-trekking"))
    sid = st.session.session_id
    with pytest.raises(Incomplete):
        run(svc.complete(sid))
    answers = {"use": "alpine", "experience": "expert", "weather": "wet", "crampons": "auto",
               "priorities": ["grip"], "wide": False, "budget": 400}
    while not st.done:
        st = run(svc.answer(sid, st.question.id, answers[st.question.id]))
    s = run(svc.complete(sid))
    slots = run(svc.present(s))
    assert 3 <= len(slots) <= 8 or len(slots) == len(s.result.slots)
    assert slots[0].role == "best_match"
    for sl in slots:
        a = sl.view.product.attributes
        assert a["crampon"] == "auto" and a["waterproof"]
        assert sl.view.affiliate_url.startswith("https://www.amazon.it/dp/")

    # modifica di una risposta precedente -> ricalcolo
    st = run(svc.answer(sid, "use", "walk"))
    assert "crampons" not in st.session.answers
    while not st.done:
        st = run(svc.answer(sid, st.question.id, {"ankle": "any"}.get(st.question.id, answers.get(st.question.id))))
    s2 = run(svc.complete(sid))
    assert s2.result.slots[0].scored.product_id != s.result.slots[0].scored.product_id
