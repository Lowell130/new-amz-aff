"""Schemi delle risposte API (separati dai modelli di dominio: non esporre la logica interna)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.finder import Explainability, FinderDefinition, FinderQuestion
from app.models.product import ProductView


class OptionOut(BaseModel):
    value: str
    label: str
    hint: str | None = None


class QuestionOut(BaseModel):
    id: str
    question: str
    help: str | None = None
    type: str
    required: bool
    options: list[OptionOut] = Field(default_factory=list)
    max_choices: int | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    unit: str | None = None
    default: Any = None

    @classmethod
    def of(cls, q: FinderQuestion) -> "QuestionOut":
        return cls(
            id=q.id, question=q.question, help=q.help, type=q.type, required=q.required,
            options=[OptionOut(value=o.value, label=o.label, hint=o.hint) for o in q.options],
            max_choices=q.max_choices, min=q.min, max=q.max, step=q.step, unit=q.unit, default=q.default,
        )


class StepOut(BaseModel):
    session_id: str
    finder_slug: str
    done: bool
    question: QuestionOut | None
    progress: dict[str, int]
    answers: dict[str, Any]


class AnswerIn(BaseModel):
    question_id: str = Field(max_length=64)
    value: Any = None


class OfferOut(BaseModel):
    price: float | None
    currency: str | None
    availability: str | None
    image_url: str | None
    fetched_at: datetime
    source: str


class ProductCard(BaseModel):
    id: str
    slug: str
    name: str
    brand: str
    asin: str
    is_demo: bool
    attributes: dict[str, Any]
    pros: list[str]
    cons: list[str]
    affiliate_url: str | None
    offer: OfferOut | None

    @classmethod
    def of(cls, v: ProductView) -> "ProductCard":
        p = v.product
        offer = None
        # Mostriamo il prezzo SOLO se lo snapshot è ancora valido.
        if v.offer and v.offer.is_valid():
            offer = OfferOut(
                price=v.offer.price.amount if v.offer.price else None,
                currency=v.offer.price.currency if v.offer.price else None,
                availability=v.offer.availability,
                image_url=v.offer.image_url,
                fetched_at=v.offer.fetched_at,
                source=v.offer.source,
            )
        return cls(
            id=p.id, slug=p.slug, name=p.name, brand=p.brand, asin=p.asin, is_demo=p.is_demo,
            attributes=p.attributes, pros=p.pros, cons=p.cons, affiliate_url=v.affiliate_url, offer=offer,
        )


class SlotOut(BaseModel):
    role: str
    label: str
    score: float
    confidence: str
    explain: Explainability
    product: ProductCard


class ProfileSummary(BaseModel):
    budget_max: float | None
    experience: str | None
    use_cases: list[str]
    priorities: list[str]
    requirements: list[str]


class ResultOut(BaseModel):
    session_id: str
    finder_slug: str
    profile: ProfileSummary
    slots: list[SlotOut]
    considered: int
    excluded: int
    generated_at: datetime
    attribute_labels: dict[str, str]


class FinderSummary(BaseModel):
    slug: str
    title: str
    short_description: str
    questions: int


class FinderDetail(FinderSummary):
    seo: dict[str, Any]
    attribute_labels: dict[str, str]
    use_case_labels: dict[str, str]

    @classmethod
    def of(cls, f: FinderDefinition) -> "FinderDetail":
        return cls(
            slug=f.slug, title=f.title, short_description=f.short_description, questions=len(f.questions),
            seo=f.seo.model_dump(), attribute_labels=f.attribute_labels, use_case_labels=f.use_case_labels,
        )


class Page(BaseModel):
    items: list[ProductCard]
    page: int
    page_size: int
    total: int


# ------------------------------------------------------------------ configuratore
class ComponentOut(BaseModel):
    key: str
    label: str
    required: bool
    why: str | None = None
    attribute_labels: dict[str, str] = Field(default_factory=dict)


class ConfiguratorSummary(BaseModel):
    slug: str
    title: str
    short_description: str
    components: int


class ConfiguratorDetail(BaseModel):
    slug: str
    title: str
    short_description: str
    seo: dict[str, Any]
    inputs: list[QuestionOut]
    components: list[ComponentOut]


class BuildIn(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    include_optional: list[str] | None = None


class SwapIn(BaseModel):
    component_key: str = Field(max_length=64)
    product_id: str = Field(max_length=200)


class AlternativeOut(BaseModel):
    product: ProductCard
    score: float
    price_delta: float | None  # differenza di prezzo rispetto al prodotto attuale
    price_is_estimate: bool


class ConfigItemOut(BaseModel):
    component_key: str
    label: str
    required: bool
    why: str | None
    score: float
    confidence: str
    explain: Explainability
    product: ProductCard
    upgrade: AlternativeOut | None
    downgrade: AlternativeOut | None


class SkippedOut(BaseModel):
    component_key: str
    label: str
    reason: str


class ConfigurationOut(BaseModel):
    session_id: str
    template_slug: str
    budget: float
    profile: ProfileSummary
    items: list[ConfigItemOut]
    skipped: list[SkippedOut]
    total_valid: float  # somma dei soli prezzi aggiornati
    missing_prices: int
    residual: float | None  # solo se tutti i prezzi sono aggiornati
    over_budget: bool
    generated_at: datetime
    answers: dict[str, Any] = Field(default_factory=dict)  # per ricaricare il modulo già compilato
    include_optional: list[str] | None = None


# ---------------------------------------------------------------------- advisor
class QuickReplyOut(BaseModel):
    question_id: str
    value: Any
    label: str


class QuickReplyIn(BaseModel):
    question_id: str = Field(max_length=64)
    value: Any = None


class AdvisorMessageIn(BaseModel):
    session_id: str = Field(max_length=64)
    text: str | None = Field(default=None, max_length=1000)
    quick_reply: QuickReplyIn | None = None


class AdvisorTargetOut(BaseModel):
    kind: str
    slug: str
    title: str


class AdvisorReplyOut(BaseModel):
    session_id: str
    text: str
    text_source: str
    quick_replies: list[QuickReplyOut]
    understood: list[str]
    target: AdvisorTargetOut | None
    finder_result: ResultOut | None = None
    configuration: ConfigurationOut | None = None
    open_url: str | None = None
    open_label: str | None = None
