"""Adapter per la Amazon Creators API (Fase 11 della roadmap).

VOLUTAMENTE NON IMPLEMENTATO: gli endpoint, l'autenticazione e il formato delle risposte
vanno presi esclusivamente dalla documentazione ufficiale corrente del Programma
Affiliazione Amazon, non inventati. Operazioni previste dalla documentazione:
SearchItems, GetItems, GetVariations, GetBrowseNodes.

Requisiti da rispettare quando lo si implementa:
- SearchItems restituisce al massimo 10 risultati per richiesta (paginare).
- GetItems accetta più ASIN per richiesta: raggruppare le chiamate.
- I dati restituiti (prezzo, disponibilità, link immagini) vanno salvati SOLO come
  ProviderSnapshot con expires_at <= 24h (vedi ProductDataService).
- L'accesso all'API richiede vendite idonee recenti: finché non c'è, usare il mock.
"""

from __future__ import annotations

from app.models.product import ProviderSnapshot
from app.providers.base import ProviderNotConfigured, SearchHit


class AmazonCreatorsProvider:
    name = "amazon"

    def __init__(self, *, credential_id: str | None, credential_secret: str | None, partner_tag: str | None):
        self._configured = bool(credential_id and credential_secret and partner_tag)
        self._credential_id = credential_id
        self._credential_secret = credential_secret
        self._partner_tag = partner_tag

    def _not_ready(self) -> ProviderNotConfigured:
        if not self._configured:
            return ProviderNotConfigured("Credenziali Amazon Creators API mancanti (vedi .env.example)")
        return ProviderNotConfigured("AmazonCreatorsProvider non ancora implementato (Fase 11)")

    async def search_products(self, keywords: str, *, category: str | None = None, page: int = 1) -> list[SearchHit]:
        raise self._not_ready()

    async def get_products(self, asins: list[str], *, marketplace: str = "it") -> list[ProviderSnapshot]:
        raise self._not_ready()

    async def get_variations(self, asin: str, *, marketplace: str = "it") -> list[ProviderSnapshot]:
        raise self._not_ready()

    async def get_category(self, category_id: str) -> dict:
        raise self._not_ready()
