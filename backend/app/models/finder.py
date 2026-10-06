"""Modelli del Product Finder: definizione del questionario, profilo utente, sessione, risultato."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

QuestionType = Literal["single_choice", "multiple_choice", "range", "boolean", "number"]


class Requirement(BaseModel):
    """Vincolo su un attributo del prodotto.

    hard=True  -> il prodotto viene escluso se non lo rispetta
    hard=False -> il prodotto resta in classifica ma riceve una penalità
    """

    attr: str
    op: Literal["eq", "in", "gte", "lte"] = "eq"
    value: Any
    hard: bool = False
    label: str  # testo leggibile, es. "impermeabile"


class ProfilePatch(BaseModel):
    """Effetto che una risposta ha sul profilo utente."""

    budget_min: float | None = None
    budget_max: float | None = None
    experience: str | None = None
    use_cases: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)


class Condition(BaseModel):
    """La domanda viene mostrata solo se la risposta a `question` è in `in_`."""

    question: str
    in_: list[Any] = Field(alias="in")

    model_config = {"populate_by_name": True}


class FinderOption(BaseModel):
    value: str
    label: str
    hint: str | None = None
    patch: ProfilePatch = Field(default_factory=ProfilePatch)


class FinderQuestion(BaseModel):
    id: str
    question: str
    help: str | None = None
    type: QuestionType
    required: bool = True
    order: int = 0
    options: list[FinderOption] = Field(default_factory=list)
    condition: Condition | None = None
    max_choices: int | None = None  # per multiple_choice
    # per range / number / boolean
    min: float | None = None
    max: float | None = None
    step: float | None = None
    unit: str | None = None
    maps_to: str | None = None  # es. "budget_max" per range/number
    patch_if_true: ProfilePatch | None = None  # per boolean
    default: Any = None


class PriorityRule(BaseModel):
    """Come una priorità dell'utente si traduce in un punteggio sui prodotti.

    numeric: direction higher/lower, normalizzato min-max sui candidati
    boolean: equals=True/False
    """

    key: str
    label: str
    attr: str
    direction: Literal["higher", "lower"] | None = None
    equals: Any = None
    unit: str | None = None
    reason_template: str  # es. "Tra le più leggere della selezione ({value} {unit})"


class ScoringWeights(BaseModel):
    budget: float = 0.25
    use_case: float = 0.25
    experience: float = 0.10
    priorities: float = 0.30
    requirements: float = 0.10


class FinderSEO(BaseModel):
    title: str
    description: str
    h1: str
    intro: str
    guide_sections: list[dict[str, str]] = Field(default_factory=list)  # [{title, body}]
    faq: list[dict[str, str]] = Field(default_factory=list)  # [{q, a}]


class FinderDefinition(BaseModel):
    slug: str
    category: str
    title: str
    short_description: str
    questions: list[FinderQuestion]
    priority_rules: list[PriorityRule] = Field(default_factory=list)
    use_case_labels: dict[str, str] = Field(default_factory=dict)
    experience_labels: dict[str, str] = Field(default_factory=dict)
    attribute_labels: dict[str, str] = Field(default_factory=dict)  # per la tabella confronto
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    budget_tolerance: float = 0.15  # oltre budget*(1+tol) il prodotto è escluso
    seo: FinderSEO
    published: bool = True


class UserProfile(BaseModel):
    budget_min: float | None = None
    budget_max: float | None = None
    experience: str | None = None
    use_cases: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)


class Explainability(BaseModel):
    matched: list[str] = Field(default_factory=list)
    weak_matches: list[str] = Field(default_factory=list)
    missing_features: list[str] = Field(default_factory=list)
    penalties: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class ScoredProduct(BaseModel):
    product_id: str
    score: float
    components: dict[str, float]
    confidence: Literal["alta", "media", "bassa"]
    explain: Explainability
    price_for_ranking: float | None = None
    price_is_estimate: bool = True


class RecommendationSlot(BaseModel):
    role: Literal["best_match", "cheaper", "premium", "alternative"]
    label: str
    scored: ScoredProduct


class FinderResult(BaseModel):
    profile: UserProfile
    slots: list[RecommendationSlot]
    considered: int
    excluded: int
    generated_at: datetime


class FinderSession(BaseModel):
    session_id: str
    finder_slug: str
    answers: dict[str, Any] = Field(default_factory=dict)
    status: Literal["active", "completed"] = "active"
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    profile: UserProfile | None = None
    result: FinderResult | None = None
