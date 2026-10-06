"""Endpoint del Configuratore."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_container, rate_limit
from app.api.schemas import (
    AlternativeOut,
    BuildIn,
    ComponentOut,
    ConfigItemOut,
    ConfigurationOut,
    ConfiguratorDetail,
    ConfiguratorSummary,
    ProductCard,
    ProfileSummary,
    QuestionOut,
    SkippedOut,
    SwapIn,
)
from app.core.container import Container
from app.models.configurator import ConfigurationTemplate
from app.models.finder import ScoredProduct
from app.models.product import ProductView
from app.scoring.configurator import BudgetTooLow, ComponentNotFound
from app.scoring.flow import InvalidAnswer
from app.services.configurator import PresentedConfiguration
from app.services.finder import NotFound

router = APIRouter(prefix="/api", tags=["configurator"])


def _http(e: Exception) -> HTTPException:
    if isinstance(e, NotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    if isinstance(e, BudgetTooLow):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Con questo budget non riusciamo a comporre il kit essenziale: servono almeno circa {e.min_needed:.0f} €.",
        )
    if isinstance(e, (InvalidAnswer, ComponentNotFound)):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    raise e


def _alt(alt: ScoredProduct | None, view: ProductView | None, current: ScoredProduct) -> AlternativeOut | None:
    if not alt or not view:
        return None
    delta = None
    if alt.price_for_ranking is not None and current.price_for_ranking is not None:
        delta = round(alt.price_for_ranking - current.price_for_ranking, 2)
    return AlternativeOut(
        product=ProductCard.of(view), score=alt.score, price_delta=delta,
        price_is_estimate=alt.price_is_estimate or current.price_is_estimate,
    )


def _profile(t: ConfigurationTemplate, p) -> ProfileSummary:
    labels = {r.key: r.label for c in t.components for r in c.priority_rules}
    return ProfileSummary(
        budget_max=p.budget_max,
        experience=t.experience_labels.get(p.experience or "", p.experience),
        use_cases=[t.use_case_labels.get(u, u) for u in p.use_cases],
        priorities=[labels.get(k, k) for k in p.priorities],
        requirements=[r.label for r in p.requirements],
    )


def _out(pc: PresentedConfiguration) -> ConfigurationOut:
    t, s = pc.template, pc.session
    why = {c.key: c.why for c in t.components}
    return ConfigurationOut(
        session_id=s.session_id,
        template_slug=s.template_slug,
        budget=s.result.budget,
        profile=_profile(t, s.result.profile),
        items=[
            ConfigItemOut(
                component_key=pi.item.component_key, label=pi.item.label, required=pi.item.required,
                why=why.get(pi.item.component_key), score=pi.item.scored.score,
                confidence=pi.item.scored.confidence, explain=pi.item.scored.explain,
                product=ProductCard.of(pi.view),
                upgrade=_alt(pi.item.upgrade, pi.upgrade, pi.item.scored),
                downgrade=_alt(pi.item.downgrade, pi.downgrade, pi.item.scored),
            )
            for pi in pc.items
        ],
        skipped=[SkippedOut(**sk.model_dump()) for sk in s.result.skipped],
        total_valid=pc.total_valid,
        missing_prices=pc.missing_prices,
        residual=pc.residual,
        over_budget=s.result.over_budget,
        generated_at=s.result.generated_at,
    )


@router.get("/configurators", response_model=list[ConfiguratorSummary])
async def list_configurators(c: Container = Depends(get_container)):
    return [
        ConfiguratorSummary(slug=t.slug, title=t.title, short_description=t.short_description, components=len(t.components))
        for t in await c.repos.configurators.list_published()
    ]


@router.get("/configurators/{slug}", response_model=ConfiguratorDetail)
async def get_configurator(slug: str, c: Container = Depends(get_container)):
    try:
        t = await c.configurator.get_template(slug)
    except NotFound as e:
        raise _http(e)
    return ConfiguratorDetail(
        slug=t.slug, title=t.title, short_description=t.short_description, seo=t.seo.model_dump(),
        inputs=[QuestionOut.of(q) for q in sorted(t.inputs, key=lambda q: q.order)],
        components=[ComponentOut(key=x.key, label=x.label, required=x.required, why=x.why,
                                 attribute_labels=x.attribute_labels) for x in t.components],
    )


@router.post("/configurators/{slug}/build", response_model=ConfigurationOut, dependencies=[Depends(rate_limit)])
async def build(slug: str, body: BuildIn, c: Container = Depends(get_container)):
    try:
        s = await c.configurator.build(slug, body.answers, body.include_optional)
        t = await c.configurator.get_template(slug)
        return _out(await c.configurator.present(s, t))
    except (NotFound, BudgetTooLow, InvalidAnswer) as e:
        raise _http(e)


@router.get("/configuration/{session_id}", response_model=ConfigurationOut)
async def get_configuration(session_id: str, c: Container = Depends(get_container)):
    """Configurazione caricabile via URL (pagina noindex lato frontend)."""
    try:
        s, t = await c.configurator.get_session(session_id)
        return _out(await c.configurator.present(s, t))
    except NotFound as e:
        raise _http(e)


@router.post("/configuration/{session_id}/swap", response_model=ConfigurationOut, dependencies=[Depends(rate_limit)])
async def swap(session_id: str, body: SwapIn, c: Container = Depends(get_container)):
    """Sostituzione esplicita di un componente (upgrade/downgrade). Può superare il budget: viene segnalato."""
    try:
        s = await c.configurator.swap(session_id, body.component_key, body.product_id)
        t = await c.configurator.get_template(s.template_slug)
        return _out(await c.configurator.present(s, t))
    except (NotFound, ComponentNotFound) as e:
        raise _http(e)
