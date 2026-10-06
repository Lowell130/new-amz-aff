"""Modelli di dominio del prodotto.

Il prodotto è diviso in tre blocchi con regole di conservazione diverse:

1. IDENTITÀ STABILE   -> asin, marketplace, brand, category, slug (conservabili)
2. DATI DEL PROVIDER  -> ProviderSnapshot (temporanei, scadenza <= 24h, mai permanenti)
3. DATI EDITORIALI    -> attributi normalizzati, use case, pro/contro, note (nostri)

Il prezzo del provider NON è mai un dato permanente del prodotto: vive solo nello
snapshot, che ha una scadenza (TTL in MongoDB). `reference_price` è una nostra stima
editoriale usata SOLO per il ranking e non viene mai mostrata come prezzo corrente.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Money(BaseModel):
    amount: float
    currency: str = "EUR"


class ProviderSnapshot(BaseModel):
    """Dati temporanei restituiti dal provider (Amazon o mock)."""

    asin: str
    marketplace: str = "it"
    source: str  # "mock" | "amazon"
    title: str | None = None
    price: Money | None = None
    availability: str | None = None
    image_url: str | None = None  # solo il link, mai l'immagine scaricata
    fetched_at: datetime
    expires_at: datetime

    def is_valid(self, now: datetime | None = None) -> bool:
        now = now or utcnow()
        exp = self.expires_at
        if exp.tzinfo is None:  # Mongo restituisce datetime naive in UTC
            exp = exp.replace(tzinfo=timezone.utc)
        return exp > now


class Product(BaseModel):
    # --- identità stabile ---
    id: str  # = slug, chiave interna
    asin: str
    marketplace: str = "it"
    brand: str
    category: str  # categoria interna (es. "scarpe-trekking")
    slug: str
    name: str  # nome editoriale (nostro), non il titolo Amazon
    is_demo: bool = False

    # --- dati editoriali della piattaforma ---
    attributes: dict[str, Any] = Field(default_factory=dict)
    use_cases: list[str] = Field(default_factory=list)
    unsuitable_for: list[str] = Field(default_factory=list)
    levels: list[str] = Field(default_factory=list)  # beginner/intermediate/expert
    tags: list[str] = Field(default_factory=list)
    reference_price: float | None = None  # stima editoriale, solo per ranking
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    editorial_notes: str | None = None
    compatible_with: list[str] = Field(default_factory=list)
    incompatible_with: list[str] = Field(default_factory=list)


class ProductView(BaseModel):
    """Prodotto + eventuale snapshot valido, pronto per essere mostrato."""

    product: Product
    offer: ProviderSnapshot | None = None
    affiliate_url: str | None = None

    @property
    def current_price(self) -> float | None:
        if self.offer and self.offer.price and self.offer.is_valid():
            return self.offer.price.amount
        return None

    @property
    def ranking_price(self) -> float | None:
        """Prezzo usato per il ranking: offerta valida, altrimenti stima editoriale."""
        return self.current_price if self.current_price is not None else self.product.reference_price
