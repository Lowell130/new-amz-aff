"""Caricamento del dataset demo in qualunque backend (memory o Mongo)."""

from __future__ import annotations

from app.repositories.base import Repositories
from app.seed import trekking


async def seed_demo(repos: Repositories) -> dict[str, int]:
    await repos.finders.upsert(trekking.finder_definition())
    n = await repos.products.upsert_many(trekking.generate_products())
    return {"finders": 1, "products": n}
