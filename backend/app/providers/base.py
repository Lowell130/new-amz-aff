"""Interfaccia dei provider di prodotti.

Il resto dell'applicazione dipende SOLO da questa interfaccia, mai da Amazon direttamente.
Così si può sviluppare tutto con MockProductProvider e collegare Amazon (o altri merchant)
in un secondo momento.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from app.models.product import ProviderSnapshot


class ProviderError(Exception):
    """Errore generico del provider (rete, quota, risposta non valida)."""


class ProviderNotConfigured(ProviderError):
    """Credenziali mancanti o provider non ancora implementato."""


class SearchHit(BaseModel):
    asin: str
    title: str | None = None


class ProductProvider(Protocol):
    name: str

    async def search_products(
        self, keywords: str, *, category: str | None = None, page: int = 1
    ) -> list[SearchHit]:
        """Ricerca nel catalogo del provider (Amazon: max 10 risultati per pagina)."""
        ...

    async def get_products(self, asins: list[str], *, marketplace: str = "it") -> list[ProviderSnapshot]:
        """Dati aggiornati (prezzo, disponibilità, link immagine) per una lista di ASIN."""
        ...

    async def get_variations(self, asin: str, *, marketplace: str = "it") -> list[ProviderSnapshot]:
        ...

    async def get_category(self, category_id: str) -> dict:
        ...
