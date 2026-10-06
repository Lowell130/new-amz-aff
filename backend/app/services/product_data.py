"""Combina dati stabili/editoriali con i dati temporanei del provider.

- legge gli snapshot ancora validi;
- per gli ASIN mancanti interroga il provider (a blocchi) e salva snapshot con scadenza;
- se il provider non risponde, il sito continua a funzionare SENZA prezzi
  (mai mostrare prezzi scaduti come se fossero attuali).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from app.models.product import Product, ProductView, ProviderSnapshot
from app.providers.base import ProductProvider, ProviderError
from app.repositories.base import SnapshotRepository
from app.services.affiliate import AffiliateLinkError, AffiliateLinkService

log = logging.getLogger(__name__)

MAX_TTL = timedelta(hours=24)
BATCH_SIZE = 10


class ProductDataService:
    def __init__(
        self,
        provider: ProductProvider,
        snapshots: SnapshotRepository,
        affiliate: AffiliateLinkService,
    ):
        self.provider = provider
        self.snapshots = snapshots
        self.affiliate = affiliate

    async def offers_for(self, products: list[Product]) -> dict[str, ProviderSnapshot]:
        if not products:
            return {}
        by_mk: dict[str, list[str]] = {}
        for p in products:
            by_mk.setdefault(p.marketplace, []).append(p.asin)

        result: dict[str, ProviderSnapshot] = {}
        for mk, asins in by_mk.items():
            for s in await self.snapshots.get_valid(asins, mk):
                result[s.asin] = s
            missing = [a for a in asins if a not in result]
            for i in range(0, len(missing), BATCH_SIZE):
                chunk = missing[i : i + BATCH_SIZE]
                try:
                    fresh = await self.provider.get_products(chunk, marketplace=mk)
                except ProviderError as e:
                    log.warning("Provider %s non disponibile: %s", self.provider.name, e)
                    break  # failsafe: niente prezzi, il resto funziona
                fresh = [self._cap_ttl(s) for s in fresh]
                await self.snapshots.save_many(fresh)
                for s in fresh:
                    result[s.asin] = s
        return result

    async def views(self, products: list[Product]) -> list[ProductView]:
        offers = await self.offers_for(products)
        out = []
        for p in products:
            try:
                link = self.affiliate.build(p.asin, p.marketplace)
            except AffiliateLinkError:
                link = None
            out.append(ProductView(product=p, offer=offers.get(p.asin), affiliate_url=link))
        return out

    @staticmethod
    def _cap_ttl(s: ProviderSnapshot) -> ProviderSnapshot:
        if s.expires_at - s.fetched_at > MAX_TTL:
            return s.model_copy(update={"expires_at": s.fetched_at + MAX_TTL})
        return s
