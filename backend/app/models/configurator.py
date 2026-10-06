"""Modelli del Configuratore: un insieme coerente di prodotti (un "kit") entro un budget."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.finder import FinderQuestion, PriorityRule, ScoredProduct, ScoringWeights, UserProfile


class ComponentSpec(BaseModel):
    """Un componente del kit (es. "scarpe"), che pesca da una categoria di prodotti."""

    key: str
    label: str
    category: str
    required: bool = True
    weight: float = 1.0  # importanza del componente nel punteggio totale del kit
    priority_rules: list[PriorityRule] = Field(default_factory=list)
    # quali requisiti del profilo si applicano a questo componente (per attributo)
    requirement_attrs: list[str] = Field(default_factory=list)
    # priorità di qualità sempre considerate (peso 1), anche se l'utente non le sceglie
    default_priorities: list[str] = Field(default_factory=list)
    attribute_labels: dict[str, str] = Field(default_factory=dict)
    why: str | None = None  # perché serve (testo editoriale)


class ConfigurationSEO(BaseModel):
    title: str
    description: str
    h1: str
    intro: str


class ConfigurationTemplate(BaseModel):
    slug: str
    title: str
    short_description: str
    inputs: list[FinderQuestion]  # stesse domande/patch del Finder -> stesso UserProfile
    components: list[ComponentSpec]
    use_case_labels: dict[str, str] = Field(default_factory=dict)
    experience_labels: dict[str, str] = Field(default_factory=dict)
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    seo: ConfigurationSEO
    published: bool = True
    advisor_keywords: list[str] = Field(default_factory=list)
    advisor_key_questions: list[str] = Field(default_factory=lambda: ["use", "budget"])

    # compatibilità con le funzioni del flow (che leggono .questions)
    @property
    def questions(self) -> list[FinderQuestion]:
        return self.inputs


class ConfigItem(BaseModel):
    component_key: str
    label: str
    required: bool
    scored: ScoredProduct
    upgrade: ScoredProduct | None = None
    downgrade: ScoredProduct | None = None


class SkippedComponent(BaseModel):
    component_key: str
    label: str
    reason: str


class ConfigurationResult(BaseModel):
    profile: UserProfile
    budget: float
    items: list[ConfigItem]
    skipped: list[SkippedComponent] = Field(default_factory=list)
    total_for_ranking: float
    over_budget: bool = False  # True solo dopo una sostituzione esplicita dell'utente
    generated_at: datetime


class ConfigurationSession(BaseModel):
    session_id: str
    template_slug: str
    answers: dict[str, Any]
    include_optional: list[str] | None = None
    status: Literal["completed"] = "completed"
    created_at: datetime
    updated_at: datetime
    result: ConfigurationResult
