"""Carica il dataset demo in MongoDB e crea gli indici.

Uso:  python -m app.seed.run
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.db.mongo import create_client, ensure_indexes
from app.repositories.mongo import mongo_repositories
from app.seed.loader import seed_demo


async def main() -> None:
    s = get_settings()
    client = create_client(s.mongo_uri.get_secret_value())
    try:
        db = client[s.mongo_db]
        await ensure_indexes(db)
        print(await seed_demo(mongo_repositories(db)))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
