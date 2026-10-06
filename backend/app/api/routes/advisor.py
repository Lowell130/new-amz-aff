"""Endpoint dell'AI Advisor."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_container, rate_limit
from app.api.routes.configurator import _out as configuration_out
from app.api.routes.finder import _result as finder_result
from app.api.schemas import AdvisorMessageIn, AdvisorReplyOut, AdvisorTargetOut, QuickReplyOut
from app.core.container import Container
from app.services.advisor import AdvisorTurn
from app.services.finder import NotFound

router = APIRouter(prefix="/api/advisor", tags=["advisor"])


async def _reply(turn: AdvisorTurn, c: Container) -> AdvisorReplyOut:
    out = AdvisorReplyOut(
        session_id=turn.session.session_id,
        text=turn.text,
        text_source=turn.text_source,
        quick_replies=[QuickReplyOut(question_id=q.question_id, value=q.value, label=q.label) for q in turn.quick_replies],
        understood=turn.understood,
        target=AdvisorTargetOut(kind=turn.target.kind, slug=turn.target.slug, title=turn.target.title) if turn.target else None,
    )
    if turn.finder_session_id:
        s, _ = await c.finder.get_session(turn.finder_session_id)
        out.finder_result = await finder_result(s, c)
        out.open_url = f"/trova/{s.finder_slug}?s={s.session_id}"
        out.open_label = "Apri nel Product Finder"
    if turn.config_session_id:
        s, t = await c.configurator.get_session(turn.config_session_id)
        out.configuration = configuration_out(await c.configurator.present(s, t))
        out.open_url = f"/configura/{s.template_slug}?c={s.session_id}"
        out.open_label = "Apri nel configuratore"
    return out


@router.post("/session", response_model=AdvisorReplyOut, dependencies=[Depends(rate_limit)])
async def start(c: Container = Depends(get_container)):
    return await _reply(await c.advisor.start(), c)


@router.post("/message", response_model=AdvisorReplyOut, dependencies=[Depends(rate_limit)])
async def message(body: AdvisorMessageIn, c: Container = Depends(get_container)):
    if not body.text and not body.quick_reply:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Scrivi un messaggio")
    qr = (body.quick_reply.question_id, body.quick_reply.value) if body.quick_reply else None
    try:
        turn = await c.advisor.message(body.session_id, body.text, qr)
    except NotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return await _reply(turn, c)
