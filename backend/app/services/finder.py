"""Servizio del Product Finder: sessioni, risposte, calcolo e presentazione del risultato."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from app.models.finder import FinderDefinition, FinderQuestion, FinderResult, FinderSession
from app.models.product import ProductView, utcnow
from app.repositories.base import Repositories
from app.scoring import flow
from app.scoring.engine import ScoringEngine
from app.scoring.slots import build_slots
from app.services.product_data import ProductDataService


class NotFound(Exception):
    pass


class Incomplete(Exception):
    pass


@dataclass
class StepState:
    session: FinderSession
    question: FinderQuestion | None
    progress: dict[str, int]

    @property
    def done(self) -> bool:
        return self.question is None


@dataclass
class PresentedSlot:
    role: str
    label: str
    view: ProductView
    scored: Any  # ScoredProduct


class FinderService:
    def __init__(self, repos: Repositories, product_data: ProductDataService):
        self.repos = repos
        self.product_data = product_data

    async def get_finder(self, slug: str) -> FinderDefinition:
        f = await self.repos.finders.get(slug)
        if not f or not f.published:
            raise NotFound(f"Finder '{slug}' non trovato")
        return f

    async def get_session(self, session_id: str) -> tuple[FinderSession, FinderDefinition]:
        s = await self.repos.sessions.get(session_id)
        if not s:
            raise NotFound("Sessione non trovata o scaduta")
        return s, await self.get_finder(s.finder_slug)

    async def start(self, slug: str) -> StepState:
        finder = await self.get_finder(slug)
        now = utcnow()
        s = FinderSession(session_id=secrets.token_urlsafe(16), finder_slug=slug, created_at=now, updated_at=now)
        await self.repos.sessions.save(s)
        return StepState(s, flow.next_question(finder, {}), flow.progress(finder, {}))

    async def state(self, session_id: str) -> StepState:
        s, finder = await self.get_session(session_id)
        return StepState(s, flow.next_question(finder, s.answers), flow.progress(finder, s.answers))

    async def answer(self, session_id: str, question_id: str, value: Any) -> StepState:
        s, finder = await self.get_session(session_id)
        q = next((q for q in flow.visible_questions(finder, s.answers) if q.id == question_id), None)
        if not q:
            raise flow.InvalidAnswer("Domanda non disponibile in questa sessione")
        s.answers[question_id] = flow.validate_answer(q, value)
        # modificare una risposta precedente può rendere invisibili altre domande
        s.answers = flow.prune_answers(finder, s.answers)
        s.status = "active"
        s.result = None
        s.updated_at = utcnow()
        await self.repos.sessions.save(s)
        return StepState(s, flow.next_question(finder, s.answers), flow.progress(finder, s.answers))

    async def complete(self, session_id: str) -> FinderSession:
        s, finder = await self.get_session(session_id)
        missing = [q.id for q in flow.visible_questions(finder, s.answers) if q.required and q.id not in s.answers]
        if missing:
            raise Incomplete(f"Mancano risposte obbligatorie: {', '.join(missing)}")

        profile = flow.build_profile(finder, s.answers)
        products = await self.repos.products.all_in_category(finder.category)
        views = await self.product_data.views(products)
        ranking = ScoringEngine(finder).rank(profile, views)
        now = utcnow()
        s.profile = profile
        s.result = FinderResult(
            profile=profile,
            slots=build_slots(ranking.ranked),
            considered=len(products),
            excluded=ranking.excluded,
            generated_at=now,
        )
        s.status = "completed"
        s.completed_at = now
        s.updated_at = now
        await self.repos.sessions.save(s)
        return s

    async def present(self, session: FinderSession) -> list[PresentedSlot]:
        """Unisce il risultato salvato con dati provider AGGIORNATI al momento della visualizzazione."""
        if not session.result:
            raise Incomplete("Il questionario non è ancora stato completato")
        ids = [sl.scored.product_id for sl in session.result.slots]
        products = await self.repos.products.get_many(ids)
        views = {v.product.id: v for v in await self.product_data.views(products)}
        return [
            PresentedSlot(role=sl.role, label=sl.label, view=views[sl.scored.product_id], scored=sl.scored)
            for sl in session.result.slots
            if sl.scored.product_id in views
        ]
