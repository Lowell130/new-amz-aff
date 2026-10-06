"""Connessione MongoDB con PyMongo Async (non Motor, in via di deprecazione) e creazione indici."""

from __future__ import annotations

from pymongo import ASCENDING, DESCENDING, AsyncMongoClient, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

# Durata conservazione sessioni anonime del finder ed eventi.
SESSION_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 giorni
EVENT_TTL_SECONDS = 60 * 60 * 24 * 400  # ~13 mesi


def create_client(uri: str) -> AsyncMongoClient:
    # tz_aware=True: i datetime tornano con timezone UTC
    return AsyncMongoClient(uri, tz_aware=True, appname="product-discovery-engine")


async def ensure_indexes(db: AsyncDatabase) -> None:
    """Indici progettati prima delle query principali (vedi docs/ARCHITETTURA.md)."""
    await db.products.create_indexes(
        [
            IndexModel([("asin", ASCENDING), ("marketplace", ASCENDING)], unique=True, name="asin_marketplace"),
            IndexModel([("slug", ASCENDING)], unique=True, name="slug"),
            IndexModel([("category", ASCENDING), ("slug", ASCENDING)], name="category_slug"),
            IndexModel([("category", ASCENDING), ("use_cases", ASCENDING)], name="category_use_cases"),
        ]
    )
    await db.product_snapshots.create_indexes(
        [
            IndexModel([("asin", ASCENDING), ("marketplace", ASCENDING)], unique=True, name="asin_marketplace"),
            # TTL: MongoDB cancella automaticamente gli snapshot scaduti (regola max 24h)
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_expires_at"),
        ]
    )
    await db.finders.create_indexes([IndexModel([("slug", ASCENDING)], unique=True, name="slug")])
    await db.finder_sessions.create_indexes(
        [
            IndexModel([("session_id", ASCENDING)], unique=True, name="session_id"),
            IndexModel([("created_at", ASCENDING)], expireAfterSeconds=SESSION_TTL_SECONDS, name="ttl_created_at"),
        ]
    )
    await db.click_events.create_indexes(
        [
            IndexModel([("type", ASCENDING), ("ts", DESCENDING)], name="type_ts"),
            IndexModel([("ts", ASCENDING)], expireAfterSeconds=EVENT_TTL_SECONDS, name="ttl_ts"),
        ]
    )
