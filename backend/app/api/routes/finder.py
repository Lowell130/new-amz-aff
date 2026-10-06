"""Endpoint del Product Finder."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_container, rate_limit
from app.api.schemas import (
    AnswerIn,
    FinderDetail,
    FinderSummary,
    ProductCard,
    ProfileSummary,
    QuestionOut,
    ResultOut,
    SlotOut,
    StepOut,
)
from app.core.container import Container
from app.models.finder import FinderSession
from app.scoring.flow import InvalidAnswer
from app.services.finder import Incomplete, NotFound, StepState

router = APIRouter(prefix="/api", tags=["finder"])


def _step(st: StepState) -> StepOut:
    return StepOut(
        session_id=st.session.session_id,
        finder_slug=st.session.finder_slug,
        done=st.done,
        question=QuestionOut.of(st.question) if st.question else None,
        progress=st.progress,
        answers=st.session.answers,
    )


def _errors(e: Exception) -> HTTPException:
    if isinstance(e, NotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    if isinstance(e, (InvalidAnswer, Incomplete)):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    raise e


@router.get("/finders", response_model=list[FinderSummary])
async def list_finders(c: Container = Depends(get_container)):
    return [
        FinderSummary(slug=f.slug, title=f.title, short_description=f.short_description, questions=len(f.questions))
        for f in await c.repos.finders.list_published()
    ]


@router.get("/finders/{slug}", response_model=FinderDetail)
async def get_finder(slug: str, c: Container = Depends(get_container)):
    try:
        return FinderDetail.of(await c.finder.get_finder(slug))
    except NotFound as e:
        raise _errors(e)


@router.post("/finder/{slug}/start", response_model=StepOut, dependencies=[Depends(rate_limit)])
async def start(slug: str, c: Container = Depends(get_container)):
    try:
        return _step(await c.finder.start(slug))
    except NotFound as e:
        raise _errors(e)


@router.get("/finder/session/{session_id}", response_model=StepOut)
async def session_state(session_id: str, c: Container = Depends(get_container)):
    try:
        return _step(await c.finder.state(session_id))
    except NotFound as e:
        raise _errors(e)


@router.get("/finder/session/{session_id}/question/{question_id}", response_model=QuestionOut)
async def get_question(session_id: str, question_id: str, c: Container = Depends(get_container)):
    """Per tornare indietro: restituisce una domanda già vista (con la risposta in session.answers)."""
    try:
        s, finder = await c.finder.get_session(session_id)
    except NotFound as e:
        raise _errors(e)
    q = next((q for q in finder.questions if q.id == question_id), None)
    if not q:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Domanda non trovata")
    return QuestionOut.of(q)


@router.post("/finder/session/{session_id}/answer", response_model=StepOut, dependencies=[Depends(rate_limit)])
async def answer(session_id: str, body: AnswerIn, c: Container = Depends(get_container)):
    try:
        return _step(await c.finder.answer(session_id, body.question_id, body.value))
    except (NotFound, InvalidAnswer) as e:
        raise _errors(e)


async def _result(s: FinderSession, c: Container) -> ResultOut:
    finder = await c.finder.get_finder(s.finder_slug)
    presented = await c.finder.present(s)
    p = s.result.profile
    return ResultOut(
        session_id=s.session_id,
        finder_slug=s.finder_slug,
        profile=ProfileSummary(
            budget_max=p.budget_max,
            experience=finder.experience_labels.get(p.experience or "", p.experience),
            use_cases=[finder.use_case_labels.get(u, u) for u in p.use_cases],
            priorities=[next((r.label for r in finder.priority_rules if r.key == k), k) for k in p.priorities],
            requirements=[r.label for r in p.requirements],
        ),
        slots=[
            SlotOut(
                role=ps.role, label=ps.label, score=ps.scored.score, confidence=ps.scored.confidence,
                explain=ps.scored.explain, product=ProductCard.of(ps.view),
            )
            for ps in presented
        ],
        considered=s.result.considered,
        excluded=s.result.excluded,
        generated_at=s.result.generated_at,
        attribute_labels=finder.attribute_labels,
    )


@router.post("/finder/session/{session_id}/complete", response_model=ResultOut, dependencies=[Depends(rate_limit)])
async def complete(session_id: str, c: Container = Depends(get_container)):
    try:
        s = await c.finder.complete(session_id)
        return await _result(s, c)
    except (NotFound, Incomplete) as e:
        raise _errors(e)


@router.get("/finder/session/{session_id}/result", response_model=ResultOut)
async def result(session_id: str, c: Container = Depends(get_container)):
    """Risultato caricabile via URL (pagina noindex lato frontend)."""
    try:
        s, _ = await c.finder.get_session(session_id)
        return await _result(s, c)
    except (NotFound, Incomplete) as e:
        raise _errors(e)
