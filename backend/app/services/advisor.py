"""AI Advisor: conversazione -> requisiti strutturati -> motori deterministici -> spiegazione.

Flusso di ogni messaggio:
  1. estrazione (LLM con schema JSON, oppure regole) delle risposte alle domande esistenti;
  2. scelta dello strumento (Finder o Configuratore) e validazione delle risposte;
  3. se manca un'informazione indispensabile -> UNA domanda mirata con risposte rapide;
  4. altrimenti ScoringEngine / ConfigurationEngine scelgono i prodotti;
  5. l'LLM spiega il risultato usando solo i dati passati (testo verificato, con fallback).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any

from app.ai.advisor_llm import AdvisorLLM, Target
from app.models.advisor import AdvisorSession
from app.models.events import TrackEvent
from app.models.finder import FinderQuestion
from app.models.product import utcnow
from app.repositories.base import Repositories
from app.scoring import flow
from app.scoring.configurator import BudgetTooLow
from app.services.configurator import ConfiguratorService, PresentedConfiguration
from app.services.finder import FinderService, NotFound, PresentedSlot

TARGET_QID = "__target"
MAX_TEXT = 1000


@dataclass
class QuickReply:
    question_id: str
    value: Any
    label: str


@dataclass
class AdvisorTurn:
    session: AdvisorSession
    text: str
    text_source: str = "template"  # "llm" | "template"
    quick_replies: list[QuickReply] = field(default_factory=list)
    understood: list[str] = field(default_factory=list)
    target: Target | None = None
    finder_session_id: str | None = None
    config_session_id: str | None = None


def _nice(v: float, step: float) -> float:
    unit = 50 if v >= 200 else 10
    return max(step, round(v / unit) * unit)


def budget_presets(q: FinderQuestion, minimum: float | None = None) -> list[float]:
    lo, hi = q.min or 0, q.max or 1000
    if minimum:
        lo = max(lo, minimum)
        return sorted({_nice(min(hi, lo * f), q.step or 10) for f in (1.05, 1.3, 1.7)})
    return sorted({_nice(lo + (hi - lo) * f, q.step or 10) for f in (0.15, 0.3, 0.5)})


def _eur(x: float) -> str:
    return f"{x:,.0f} €".replace(",", ".")


class AdvisorService:
    def __init__(self, repos: Repositories, finder: FinderService, configurator: ConfiguratorService, llm: AdvisorLLM):
        self.repos = repos
        self.finder = finder
        self.configurator = configurator
        self.llm = llm

    # ------------------------------------------------------------- strumenti
    async def targets(self) -> list[Target]:
        out: list[Target] = []
        for f in await self.repos.finders.list_published():
            out.append(Target(f"finder:{f.slug}", "finder", f.slug, f.title, f.short_description,
                              f.questions, f.advisor_keywords, f.advisor_key_questions))
        for t in await self.repos.configurators.list_published():
            out.append(Target(f"configurator:{t.slug}", "configurator", t.slug, t.title, t.short_description,
                              t.inputs, t.advisor_keywords, t.advisor_key_questions))
        return out

    @staticmethod
    def _target_replies(targets: list[Target]) -> list[QuickReply]:
        return [QuickReply(TARGET_QID, t.key, t.title) for t in targets]

    # --------------------------------------------------------------- sessione
    async def start(self) -> AdvisorTurn:
        now = utcnow()
        s = AdvisorSession(session_id=secrets.token_urlsafe(16), created_at=now, updated_at=now)
        s.state.pending_question = TARGET_QID
        await self.repos.advisor_sessions.save(s)
        targets = await self.targets()
        names = " oppure ".join(t.title.lower() for t in targets)
        text = (
            "Ciao! Raccontami cosa devi fare, come e con quale budget: ti aiuto a scegliere "
            f"({names}). Per esempio: \"Ho 400 euro e voglio iniziare a fare trekking in giornata\"."
        )
        return AdvisorTurn(session=s, text=text, quick_replies=self._target_replies(targets))

    async def message(self, session_id: str, text: str | None = None,
                      quick_reply: tuple[str, Any] | None = None) -> AdvisorTurn:
        s = await self.repos.advisor_sessions.get(session_id)
        if not s:
            raise NotFound("Conversazione non trovata o scaduta")
        targets = await self.targets()
        by_key = {t.key: t for t in targets}
        current = by_key.get(s.state.target or "")
        pending = self._question(current, targets, s.state.pending_question)
        off_topic = False
        changed = True

        if quick_reply is not None:
            qid, value = quick_reply
            if qid == TARGET_QID:
                if value in by_key:
                    s.state.target = value
            else:
                s.state.answers[qid] = value
        elif text:
            ex = await self.llm.extract(text[:MAX_TEXT], targets, s.state.answers, pending)
            if ex.target:
                s.state.target = ex.target
            s.state.answers.update(ex.answers)
            off_topic = ex.off_topic
            changed = bool(ex.target or ex.answers)
            await self._event("requirements_extracted", s, {"page": ex.source})

        s.turns += 1
        s.updated_at = utcnow()
        target = by_key.get(s.state.target or "") or self._infer_target(targets, s.state.answers)
        if target:
            s.state.target = target.key

        # 0) messaggio senza informazioni nuove dopo una proposta -> nessun ricalcolo
        has_result = bool(s.last_finder_session or s.last_config_session)
        if not changed and has_result and s.state.pending_question is None:
            await self.repos.advisor_sessions.save(s)
            text = ("Posso aiutarti solo nella scelta dell'attrezzatura. " if off_topic else "") + \
                "Se vuoi cambiare qualcosa della proposta (budget, uso, priorità) scrivimelo."
            return AdvisorTurn(session=s, text=text, target=target)

        # 1) strumento non chiaro -> chiedilo
        if not target:
            s.state.pending_question = TARGET_QID
            await self.repos.advisor_sessions.save(s)
            intro = "Posso aiutarti solo nella scelta dell'attrezzatura. " if off_topic else ""
            return AdvisorTurn(session=s, text=intro + "Cosa ti serve?", quick_replies=self._target_replies(targets))

        clean = self._clean_answers(target, s.state.answers)
        understood = self._understood(target, clean)

        # 2) manca un'informazione indispensabile -> UNA domanda
        missing = self._next_missing(target, clean)
        if missing:
            s.state.pending_question = missing.id
            s.state.asked.append(missing.id)
            await self.repos.advisor_sessions.save(s)
            again = s.state.asked.count(missing.id) > 1
            prefix = "Non ho capito bene. " if again else ""
            return AdvisorTurn(session=s, text=prefix + self._ask_text(missing), target=target,
                               quick_replies=self._replies_for(missing), understood=understood)

        # 3) tutto pronto -> i motori deterministici scelgono i prodotti
        s.state.pending_question = None
        if target.kind == "finder":
            turn = await self._run_finder(s, target, clean)
        else:
            turn = await self._run_configurator(s, target, clean)
        turn.understood = understood
        await self.repos.advisor_sessions.save(s)
        return turn

    # ----------------------------------------------------------- esecuzione
    async def _run_finder(self, s: AdvisorSession, target: Target, answers: dict[str, Any]) -> AdvisorTurn:
        fs = await self.finder.create_completed(target.slug, answers)
        presented = await self.finder.present(fs)
        s.last_finder_session = fs.session_id
        finder = await self.finder.get_finder(target.slug)
        payload = self._finder_payload(finder, fs.result.profile, presented)
        text, source = await self.llm.explain(payload)
        await self._event("recommendation_generated", s, {"finder_slug": target.slug})
        return AdvisorTurn(session=s, text=text + " Se vuoi cambiare qualcosa (budget, priorità, uso) scrivimelo.",
                           text_source=source, target=target, finder_session_id=fs.session_id)

    async def _run_configurator(self, s: AdvisorSession, target: Target, answers: dict[str, Any]) -> AdvisorTurn:
        try:
            cs = await self.configurator.build(target.slug, answers, None, allow_partial=True)
        except BudgetTooLow as e:
            q = next(q for q in target.questions if q.maps_to == "budget_max")
            s.state.pending_question = q.id
            return AdvisorTurn(
                session=s, target=target,
                text=f"Con questo budget non riesco a comporre il kit essenziale: servono almeno circa "
                     f"{_eur(e.min_needed)}. Vuoi aumentare il budget?",
                quick_replies=[QuickReply(q.id, v, f"Fino a {_eur(v)}") for v in budget_presets(q, e.min_needed)],
            )
        t = await self.configurator.get_template(target.slug)
        pc = await self.configurator.present(cs, t)
        s.last_config_session = cs.session_id
        payload = self._kit_payload(t, pc)
        text, source = await self.llm.explain(payload)
        await self._event("recommendation_generated", s, {"page": target.slug})
        return AdvisorTurn(session=s, text=text + " Puoi modificarlo nel configuratore o chiedermi di cambiare budget o priorità.",
                           text_source=source, target=target, config_session_id=cs.session_id)

    # ---------------------------------------------------------- payload LLM
    @staticmethod
    def _profile_payload(labels_uc: dict, labels_exp: dict, rules: dict, profile) -> dict[str, Any]:
        return {
            "uso": [labels_uc.get(u, u) for u in profile.use_cases],
            "esperienza": labels_exp.get(profile.experience or "", profile.experience),
            "priorita": [rules.get(p, p) for p in profile.priorities],
            "requisiti": [r.label for r in profile.requirements],
        }

    def _finder_payload(self, finder, profile, presented: list[PresentedSlot]) -> dict[str, Any]:
        rules = {r.key: r.label for r in finder.priority_rules}
        return {
            "tipo": "prodotto",
            "profilo": self._profile_payload(finder.use_case_labels, finder.experience_labels, rules, profile),
            "budget": profile.budget_max,
            "prodotti": [
                {
                    "ruolo": ps.label,
                    "nome": ps.view.product.name,
                    "marca": ps.view.product.brand,
                    "motivi": ps.scored.explain.reasons,
                    "compromessi": ps.scored.explain.penalties + ps.scored.explain.weak_matches,
                    "prezzo_attuale": ps.view.current_price,
                }
                for ps in presented[:3]
            ],
        }

    def _kit_payload(self, t, pc: PresentedConfiguration) -> dict[str, Any]:
        rules = {r.key: r.label for c in t.components for r in c.priority_rules}
        profile = pc.session.result.profile
        return {
            "tipo": "kit",
            "profilo": self._profile_payload(t.use_case_labels, t.experience_labels, rules, profile),
            "budget": pc.session.result.budget,
            "prodotti": [
                {
                    "ruolo": pi.item.label,
                    "nome": pi.view.product.name,
                    "marca": pi.view.product.brand,
                    "motivi": pi.item.scored.explain.reasons[:3],
                    "compromessi": pi.item.scored.explain.penalties,
                    "prezzo_attuale": pi.view.current_price,
                }
                for pi in pc.items
            ],
            "totale_prezzi_aggiornati": pc.total_valid if pc.missing_prices == 0 else None,
            "residuo": pc.residual,
            "esclusi": [sk.label for sk in pc.session.result.skipped],
        }

    # ------------------------------------------------------------- domande
    @staticmethod
    def _question(target: Target | None, targets: list[Target], qid: str | None) -> FinderQuestion | None:
        if not qid or qid == TARGET_QID:
            return None
        pool = target.questions if target else [q for t in targets for q in t.questions]
        return next((q for q in pool if q.id == qid), None)

    @staticmethod
    def _infer_target(targets: list[Target], answers: dict[str, Any]) -> Target | None:
        """Se alcune risposte esistono solo in uno strumento (es. 'ramponi'), quello è lo strumento."""
        cands = [t for t in targets if any(
            k in {q.id for q in t.questions} and all(k not in {q.id for q in o.questions} for o in targets if o is not t)
            for k in answers
        )]
        return cands[0] if len(cands) == 1 else None

    @staticmethod
    def _clean_answers(target: Target, answers: dict[str, Any]) -> dict[str, Any]:
        """Tiene solo risposte valide per lo strumento scelto (quelle non valide vengono ignorate)."""
        clean: dict[str, Any] = {}
        for q in sorted(target.questions, key=lambda q: q.order):
            if q.id not in answers or q.id not in {x.id for x in flow.visible_questions(target, clean)}:  # type: ignore[arg-type]
                continue
            value = answers[q.id]
            if q.type in ("range", "number") and isinstance(value, (int, float)):
                value = min(max(float(value), q.min if q.min is not None else value), q.max if q.max is not None else value)
            if q.type == "multiple_choice" and isinstance(value, list) and q.max_choices:
                value = value[: q.max_choices]
            try:
                clean[q.id] = flow.validate_answer(q, value)
            except flow.InvalidAnswer:
                continue
        return clean

    @staticmethod
    def _next_missing(target: Target, clean: dict[str, Any]) -> FinderQuestion | None:
        visible = {q.id for q in flow.visible_questions(target, clean)}  # type: ignore[arg-type]
        for q in sorted(target.questions, key=lambda q: q.order):
            if q.id in target.key_questions and q.id in visible and q.id not in clean:
                return q
        return None

    @staticmethod
    def _ask_text(q: FinderQuestion) -> str:
        if q.type in ("range", "number") and q.unit == "€":
            return f"{q.question} Puoi scegliere qui sotto o scrivere una cifra."
        return q.question

    @staticmethod
    def _replies_for(q: FinderQuestion) -> list[QuickReply]:
        if q.type in ("single_choice", "multiple_choice"):
            return [QuickReply(q.id, o.value if q.type == "single_choice" else [o.value], o.label) for o in q.options]
        if q.type == "boolean":
            return [QuickReply(q.id, True, "Sì"), QuickReply(q.id, False, "No")]
        if q.type in ("range", "number"):
            return [QuickReply(q.id, v, f"Fino a {_eur(v)}" if q.unit == "€" else str(v)) for v in budget_presets(q)]
        return []

    @staticmethod
    def _understood(target: Target, clean: dict[str, Any]) -> list[str]:
        out = []
        for q in sorted(target.questions, key=lambda q: q.order):
            if q.id not in clean:
                continue
            v = clean[q.id]
            labels = {o.value: o.label for o in q.options}
            if q.type == "single_choice":
                out.append(labels.get(v, str(v)))
            elif q.type == "multiple_choice":
                out += [labels.get(x, x) for x in v]
            elif q.type in ("range", "number"):
                out.append(f"Fino a {_eur(v)}" if q.unit == "€" else str(v))
            elif q.type == "boolean":
                out.append(f"{q.question.rstrip('?')}: {'sì' if v else 'no'}")
        return out

    async def _event(self, type_: str, s: AdvisorSession, payload: dict[str, Any]) -> None:
        await self.repos.events.add(TrackEvent(type=type_, session_id=s.session_id, payload=payload, ts=utcnow()).sanitized())
