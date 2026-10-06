"""Caricamento del dataset demo in qualunque backend (memory o Mongo)."""

from __future__ import annotations

from app.models.product import Product
from app.repositories.base import Repositories
from app.seed import trekking, trekking_kit


def demo_catalog() -> list[Product]:
    return trekking.generate_products() + trekking_kit.generate_products()


async def seed_demo(repos: Repositories) -> dict[str, int]:
    await repos.finders.upsert(trekking.finder_definition())
    await repos.configurators.upsert(trekking_kit.template())
    n = await repos.products.upsert_many(demo_catalog())
    return {"finders": 1, "configurators": 1, "products": n}
