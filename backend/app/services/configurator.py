"""Servizio del Configuratore: validazione input, costruzione kit, sostituzioni, presentazione."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from app.models.configurator import ConfigItem, ConfigurationSession, ConfigurationTemplate
from app.models.product import ProductView, utcnow
from app.repositories.base import Repositories
from app.scoring import flow
from app.scoring.configurator import Candidate, ConfigurationEngine
from app.services.finder import NotFound
from app.services.product_data import ProductDataService


@dataclass
class PresentedItem:
    item: ConfigItem
    view: ProductView
    upgrade: ProductView | None
    downgrade: ProductView | None


@dataclass
class PresentedConfiguration:
    session: ConfigurationSession
    template: ConfigurationTemplate
    items: list[PresentedItem]
    total_valid: float  # somma dei soli prezzi aggiornati
    missing_prices: int  # componenti senza prezzo aggiornato
    residual: float | None  # solo se tutti i prezzi sono validi


class ConfiguratorService:
    def __init__(self, repos: Repositories, product_data: ProductDataService):
        self.repos = repos
        self.product_data = product_data

    async def get_template(self, slug: str) -> ConfigurationTemplate:
        t = await self.repos.configurators.get(slug)
        if not t or not t.published:
            raise NotFound(f"Configuratore '{slug}' non trovato")
        return t

    async def get_session(self, session_id: str) -> tuple[ConfigurationSession, ConfigurationTemplate]:
        s = await self.repos.config_sessions.get(session_id)
        if not s:
            raise NotFound("Configurazione non trovata o scaduta")
        return s, await self.get_template(s.template_slug)

    # ---------------------------------------------------------------- input
    @staticmethod
    def validate_answers(t: ConfigurationTemplate, answers: dict[str, Any], allow_partial: bool = False) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        # le domande visibili dipendono dalle risposte già validate
        for q in sorted(t.inputs, key=lambda q: q.order):
            if q.id not in {x.id for x in flow.visible_questions(t, clean)}:  # type: ignore[arg-type]
                continue
            if q.id in answers and answers[q.id] is not None:
                clean[q.id] = flow.validate_answer(q, answers[q.id])
            elif q.default is not None:
                clean[q.id] = flow.validate_answer(q, q.default)
            elif q.required and not allow_partial:
                raise flow.InvalidAnswer(f"Manca la risposta: {q.question}")
        return clean

    @staticmethod
    def validate_optional(t: ConfigurationTemplate, include_optional: list[str] | None) -> list[str] | None:
        if include_optional is None:
            return None
        allowed = {c.key for c in t.components if not c.required}
        bad = [k for k in include_optional if k not in allowed]
        if bad:
            raise flow.InvalidAnswer(f"Componenti opzionali non validi: {', '.join(bad)}")
        return list(dict.fromkeys(include_optional))

    async def _candidates(self, t: ConfigurationTemplate, profile) -> dict[str, list[Candidate]]:
        engine = ConfigurationEngine(t)
        out: dict[str, list[Candidate]] = {}
        for comp in t.components:
            products = await self.repos.products.all_in_category(comp.category)
            views = await self.product_data.views(products)
            out[comp.key] = engine.candidates(profile, comp, views)
        return out

    # --------------------------------------------------------------- azioni
    async def build(
        self, slug: str, answers: dict[str, Any], include_optional: list[str] | None, allow_partial: bool = False
    ) -> ConfigurationSession:
        t = await self.get_template(slug)
        clean = self.validate_answers(t, answers, allow_partial)
        optional = self.validate_optional(t, include_optional)
        profile = flow.build_profile(t, clean)  # type: ignore[arg-type]
        if not profile.budget_max:
            raise flow.InvalidAnswer("Indica un budget")
        cands = await self._candidates(t, profile)
        result = ConfigurationEngine(t).build(profile, profile.budget_max, cands, optional)
        now = utcnow()
        s = ConfigurationSession(
            session_id=secrets.token_urlsafe(16), template_slug=slug, answers=clean,
            include_optional=optional, created_at=now, updated_at=now, result=result,
        )
        await self.repos.config_sessions.save(s)
        return s

    async def swap(self, session_id: str, component_key: str, product_id: str) -> ConfigurationSession:
        s, t = await self.get_session(session_id)
        cands = await self._candidates(t, s.result.profile)
        s.result = ConfigurationEngine(t).swap(s.result, cands, component_key, product_id)
        s.updated_at = utcnow()
        await self.repos.config_sessions.save(s)
        return s

    async def present(self, s: ConfigurationSession, t: ConfigurationTemplate) -> PresentedConfiguration:
        ids: list[str] = []
        for it in s.result.items:
            ids.append(it.scored.product_id)
            ids += [x.product_id for x in (it.upgrade, it.downgrade) if x]
        products = await self.repos.products.get_many(list(dict.fromkeys(ids)))
        views = {v.product.id: v for v in await self.product_data.views(products)}

        items: list[PresentedItem] = []
        total_valid, missing = 0.0, 0
        for it in s.result.items:
            v = views.get(it.scored.product_id)
            if not v:
                continue
            if v.current_price is not None:
                total_valid += v.current_price
            else:
                missing += 1
            items.append(PresentedItem(
                item=it, view=v,
                upgrade=views.get(it.upgrade.product_id) if it.upgrade else None,
                downgrade=views.get(it.downgrade.product_id) if it.downgrade else None,
            ))
        residual = round(s.result.budget - total_valid, 2) if missing == 0 else None
        return PresentedConfiguration(
            session=s, template=t, items=items, total_valid=round(total_valid, 2),
            missing_prices=missing, residual=residual,
        )
