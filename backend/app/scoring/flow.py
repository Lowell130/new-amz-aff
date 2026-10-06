"""Logica pura del questionario: domande visibili, domanda successiva, validazione, profilo."""

from __future__ import annotations

from typing import Any

from app.models.finder import FinderDefinition, FinderQuestion, ProfilePatch, UserProfile


class InvalidAnswer(ValueError):
    pass


def _condition_ok(q: FinderQuestion, answers: dict[str, Any]) -> bool:
    if not q.condition:
        return True
    a = answers.get(q.condition.question)
    if a is None:
        return False
    if isinstance(a, list):
        return any(x in q.condition.in_ for x in a)
    return a in q.condition.in_


def visible_questions(finder: FinderDefinition, answers: dict[str, Any]) -> list[FinderQuestion]:
    return [q for q in sorted(finder.questions, key=lambda q: q.order) if _condition_ok(q, answers)]


def prune_answers(finder: FinderDefinition, answers: dict[str, Any]) -> dict[str, Any]:
    """Rimuove le risposte a domande che, dopo una modifica, non sono più visibili."""
    current = dict(answers)
    while True:
        visible_ids = {q.id for q in visible_questions(finder, current)}
        pruned = {k: v for k, v in current.items() if k in visible_ids}
        if pruned == current:
            return pruned
        current = pruned


def next_question(finder: FinderDefinition, answers: dict[str, Any]) -> FinderQuestion | None:
    for q in visible_questions(finder, answers):
        if q.id not in answers:
            return q
    return None


def progress(finder: FinderDefinition, answers: dict[str, Any]) -> dict[str, int]:
    vis = visible_questions(finder, answers)
    return {"answered": sum(1 for q in vis if q.id in answers), "total": len(vis)}


def validate_answer(q: FinderQuestion, value: Any) -> Any:
    if value is None:
        if q.required:
            raise InvalidAnswer("Risposta obbligatoria")
        return None
    valid = {o.value for o in q.options}
    if q.type == "single_choice":
        if value not in valid:
            raise InvalidAnswer("Opzione non valida")
        return value
    if q.type == "multiple_choice":
        if not isinstance(value, list) or any(v not in valid for v in value):
            raise InvalidAnswer("Opzioni non valide")
        value = list(dict.fromkeys(value))  # deduplica mantenendo l'ordine
        if q.required and not value:
            raise InvalidAnswer("Seleziona almeno un'opzione")
        if q.max_choices and len(value) > q.max_choices:
            raise InvalidAnswer(f"Puoi scegliere al massimo {q.max_choices} opzioni")
        return value
    if q.type in ("range", "number"):
        try:
            num = float(value)
        except (TypeError, ValueError) as e:
            raise InvalidAnswer("Valore numerico non valido") from e
        if q.min is not None and num < q.min or q.max is not None and num > q.max:
            raise InvalidAnswer(f"Il valore deve essere tra {q.min} e {q.max}")
        return num
    if q.type == "boolean":
        if not isinstance(value, bool):
            raise InvalidAnswer("Valore sì/no non valido")
        return value
    raise InvalidAnswer("Tipo di domanda non supportato")


def _apply(profile: UserProfile, patch: ProfilePatch) -> None:
    if patch.budget_min is not None:
        profile.budget_min = patch.budget_min
    if patch.budget_max is not None:
        profile.budget_max = patch.budget_max
    if patch.experience:
        profile.experience = patch.experience
    for u in patch.use_cases:
        if u not in profile.use_cases:
            profile.use_cases.append(u)
    for pr in patch.priorities:
        if pr not in profile.priorities:
            profile.priorities.append(pr)
    profile.requirements.extend(patch.requirements)


def build_profile(finder: FinderDefinition, answers: dict[str, Any]) -> UserProfile:
    profile = UserProfile()
    for q in visible_questions(finder, answers):
        if q.id not in answers or answers[q.id] is None:
            continue
        a = answers[q.id]
        if q.type == "single_choice":
            opt = next(o for o in q.options if o.value == a)
            _apply(profile, opt.patch)
        elif q.type == "multiple_choice":
            for o in q.options:
                if o.value in a:
                    _apply(profile, o.patch)
        elif q.type in ("range", "number") and q.maps_to:
            setattr(profile, q.maps_to, float(a))
        elif q.type == "boolean" and a and q.patch_if_true:
            _apply(profile, q.patch_if_true)
    return profile
