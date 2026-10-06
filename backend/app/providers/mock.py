"""Provider finto: permette di sviluppare e testare tutta l'app senza credenziali Amazon.

Genera prezzi deterministici (stessi ASIN -> stessi prezzi) intorno al reference_price
del prodotto, con una piccola variazione, così il comportamento è riproducibile nei test.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta

from app.models.product import Money, Product, ProviderSnapshot, utcnow
from app.providers.base import ProviderError, SearchHit


def _stable_ratio(key: str) -> float:
    """Numero deterministico in [0, 1) derivato da una stringa."""
    h = hashlib.sha256(key.encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


class MockProductProvider:
    name = "mock"

    def __init__(self, catalog: list[Product], ttl_hours: float = 24, fail: bool = False):
        self._by_asin = {p.asin: p for p in catalog}
        self._ttl = timedelta(hours=ttl_hours)
        self.fail = fail  # per simulare un'API non disponibile nei test
        self.calls = 0

    async def search_products(self, keywords: str, *, category: str | None = None, page: int = 1) -> list[SearchHit]:
        self._check()
        kw = keywords.lower()
        hits = [
            SearchHit(asin=p.asin, title=p.name)
            for p in self._by_asin.values()
            if (kw in p.name.lower() or kw in p.brand.lower()) and (category is None or p.category == category)
        ]
        start = (page - 1) * 10
        return hits[start : start + 10]  # come Amazon: 10 risultati per pagina

    async def get_products(self, asins: list[str], *, marketplace: str = "it") -> list[ProviderSnapshot]:
        self._check()
        now = utcnow()
        out: list[ProviderSnapshot] = []
        for asin in asins:
            p = self._by_asin.get(asin)
            if not p:
                continue
            r = _stable_ratio(asin)
            base = p.reference_price or 50.0
            price = round(base * (0.9 + 0.2 * r), 2)  # +/- 10%
            available = r > 0.08  # ~8% non disponibili
            out.append(
                ProviderSnapshot(
                    asin=asin,
                    marketplace=marketplace,
                    source=self.name,
                    title=f"{p.brand} {p.name}",
                    price=Money(amount=price) if available else None,
                    availability="Disponibile" if available else "Non disponibile",
                    image_url=None,  # il frontend mostra un segnaposto per i prodotti demo
                    fetched_at=now,
                    expires_at=now + self._ttl,
                )
            )
        return out

    async def get_variations(self, asin: str, *, marketplace: str = "it") -> list[ProviderSnapshot]:
        return await self.get_products([asin], marketplace=marketplace)

    async def get_category(self, category_id: str) -> dict:
        self._check()
        return {"id": category_id, "name": category_id}

    def _check(self) -> None:
        self.calls += 1
        if self.fail:
            raise ProviderError("Mock provider: errore simulato")
