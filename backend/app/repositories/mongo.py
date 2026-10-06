"""Repository MongoDB (PyMongo Async)."""

from __future__ import annotations

from typing import Any

from pymongo import ReplaceOne
from pymongo.asynchronous.database import AsyncDatabase

from app.models.events import TrackEvent
from app.models.finder import FinderDefinition, FinderSession
from app.models.product import Product, ProviderSnapshot, utcnow
from app.repositories.base import Repositories


def _strip_id(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


class MongoProductRepository:
    def __init__(self, db: AsyncDatabase):
        self.col = db.products

    async def get(self, product_id: str) -> Product | None:
        doc = _strip_id(await self.col.find_one({"_id": product_id}))
        return Product.model_validate(doc) if doc else None

    async def get_many(self, product_ids: list[str]) -> list[Product]:
        docs = await self.col.find({"_id": {"$in": product_ids}}).to_list(None)
        by_id = {d["_id"]: Product.model_validate(_strip_id(d)) for d in docs}
        return [by_id[i] for i in product_ids if i in by_id]

    async def list_by_category(self, category: str, *, skip: int = 0, limit: int = 50) -> list[Product]:
        cur = self.col.find({"category": category}).sort("slug", 1).skip(skip).limit(limit)
        return [Product.model_validate(_strip_id(d)) for d in await cur.to_list(None)]

    async def all_in_category(self, category: str) -> list[Product]:
        # Volumi previsti per nicchia: centinaia/poche migliaia di prodotti.
        cur = self.col.find({"category": category})
        return [Product.model_validate(_strip_id(d)) for d in await cur.to_list(None)]

    async def count_by_category(self, category: str) -> int:
        return await self.col.count_documents({"category": category})

    async def upsert_many(self, products: list[Product]) -> int:
        if not products:
            return 0
        ops = [ReplaceOne({"_id": p.id}, {"_id": p.id, **p.model_dump()}, upsert=True) for p in products]
        await self.col.bulk_write(ops, ordered=False)
        return len(ops)


class MongoSnapshotRepository:
    def __init__(self, db: AsyncDatabase):
        self.col = db.product_snapshots

    async def get_valid(self, asins: list[str], marketplace: str) -> list[ProviderSnapshot]:
        cur = self.col.find({"asin": {"$in": asins}, "marketplace": marketplace, "expires_at": {"$gt": utcnow()}})
        return [ProviderSnapshot.model_validate(_strip_id(d)) for d in await cur.to_list(None)]

    async def save_many(self, snapshots: list[ProviderSnapshot]) -> None:
        if not snapshots:
            return
        ops = [
            ReplaceOne({"asin": s.asin, "marketplace": s.marketplace}, s.model_dump(), upsert=True) for s in snapshots
        ]
        await self.col.bulk_write(ops, ordered=False)


class MongoFinderRepository:
    def __init__(self, db: AsyncDatabase):
        self.col = db.finders

    async def get(self, slug: str) -> FinderDefinition | None:
        doc = _strip_id(await self.col.find_one({"slug": slug}))
        return FinderDefinition.model_validate(doc) if doc else None

    async def list_published(self) -> list[FinderDefinition]:
        docs = await self.col.find({"published": True}).to_list(None)
        return [FinderDefinition.model_validate(_strip_id(d)) for d in docs]

    async def upsert(self, finder: FinderDefinition) -> None:
        await self.col.replace_one({"slug": finder.slug}, finder.model_dump(by_alias=True), upsert=True)


class MongoSessionRepository:
    def __init__(self, db: AsyncDatabase):
        self.col = db.finder_sessions

    async def get(self, session_id: str) -> FinderSession | None:
        doc = _strip_id(await self.col.find_one({"session_id": session_id}))
        return FinderSession.model_validate(doc) if doc else None

    async def save(self, session: FinderSession) -> None:
        await self.col.replace_one({"session_id": session.session_id}, session.model_dump(), upsert=True)


class MongoEventRepository:
    def __init__(self, db: AsyncDatabase):
        self.col = db.click_events

    async def add(self, event: TrackEvent) -> None:
        await self.col.insert_one(event.model_dump())

    async def count_by_type(self) -> dict[str, int]:
        cur = await self.col.aggregate([{"$group": {"_id": "$type", "n": {"$sum": 1}}}])
        return {d["_id"]: d["n"] async for d in cur}


def mongo_repositories(db: AsyncDatabase) -> Repositories:
    return Repositories(
        products=MongoProductRepository(db),
        snapshots=MongoSnapshotRepository(db),
        finders=MongoFinderRepository(db),
        sessions=MongoSessionRepository(db),
        events=MongoEventRepository(db),
    )
