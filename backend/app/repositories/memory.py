"""Repository in memoria: per test e per provare l'app senza MongoDB (DATA_BACKEND=memory)."""

from __future__ import annotations

from collections import Counter

from app.models.events import TrackEvent
from app.models.finder import FinderDefinition, FinderSession
from app.models.product import Product, ProviderSnapshot, utcnow
from app.repositories.base import Repositories


class MemoryProductRepository:
    def __init__(self) -> None:
        self._items: dict[str, Product] = {}

    async def get(self, product_id: str) -> Product | None:
        return self._items.get(product_id)

    async def get_many(self, product_ids: list[str]) -> list[Product]:
        return [self._items[i] for i in product_ids if i in self._items]

    async def list_by_category(self, category: str, *, skip: int = 0, limit: int = 50) -> list[Product]:
        items = sorted((p for p in self._items.values() if p.category == category), key=lambda p: p.slug)
        return items[skip : skip + limit]

    async def all_in_category(self, category: str) -> list[Product]:
        return [p for p in self._items.values() if p.category == category]

    async def count_by_category(self, category: str) -> int:
        return sum(1 for p in self._items.values() if p.category == category)

    async def upsert_many(self, products: list[Product]) -> int:
        for p in products:
            self._items[p.id] = p
        return len(products)


class MemorySnapshotRepository:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], ProviderSnapshot] = {}

    async def get_valid(self, asins: list[str], marketplace: str) -> list[ProviderSnapshot]:
        now = utcnow()
        out = []
        for a in asins:
            s = self._items.get((a, marketplace))
            if s and s.is_valid(now):
                out.append(s)
        return out

    async def save_many(self, snapshots: list[ProviderSnapshot]) -> None:
        for s in snapshots:
            self._items[(s.asin, s.marketplace)] = s


class MemoryFinderRepository:
    def __init__(self) -> None:
        self._items: dict[str, FinderDefinition] = {}

    async def get(self, slug: str) -> FinderDefinition | None:
        return self._items.get(slug)

    async def list_published(self) -> list[FinderDefinition]:
        return [f for f in self._items.values() if f.published]

    async def upsert(self, finder: FinderDefinition) -> None:
        self._items[finder.slug] = finder


class MemorySessionRepository:
    def __init__(self) -> None:
        self._items: dict[str, FinderSession] = {}

    async def get(self, session_id: str) -> FinderSession | None:
        s = self._items.get(session_id)
        return s.model_copy(deep=True) if s else None

    async def save(self, session: FinderSession) -> None:
        self._items[session.session_id] = session.model_copy(deep=True)


class MemoryEventRepository:
    def __init__(self) -> None:
        self.items: list[TrackEvent] = []

    async def add(self, event: TrackEvent) -> None:
        self.items.append(event)

    async def count_by_type(self) -> dict[str, int]:
        return dict(Counter(e.type for e in self.items))


def memory_repositories() -> Repositories:
    return Repositories(
        products=MemoryProductRepository(),
        snapshots=MemorySnapshotRepository(),
        finders=MemoryFinderRepository(),
        sessions=MemorySessionRepository(),
        events=MemoryEventRepository(),
    )
