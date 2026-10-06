"""Health, prodotti, eventi di tracking, statistiche admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_container, rate_limit, require_admin
from app.api.schemas import Page, ProductCard
from app.core.container import Container
from app.models.events import TrackEvent
from app.models.product import utcnow

router = APIRouter(prefix="/api")


@router.get("/health", tags=["system"])
async def health(c: Container = Depends(get_container)):
    return {"status": "ok", "backend": c.settings.data_backend, "provider": c.provider.name}


@router.get("/products", response_model=Page, tags=["products"])
async def list_products(
    category: str = Query(..., max_length=64),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=60),
    c: Container = Depends(get_container),
):
    total = await c.repos.products.count_by_category(category)
    items = await c.repos.products.list_by_category(category, skip=(page - 1) * page_size, limit=page_size)
    views = await c.product_data.views(items)
    return Page(items=[ProductCard.of(v) for v in views], page=page, page_size=page_size, total=total)


@router.get("/products/{product_id}", response_model=ProductCard, tags=["products"])
async def get_product(product_id: str, c: Container = Depends(get_container)):
    p = await c.repos.products.get(product_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prodotto non trovato")
    [view] = await c.product_data.views([p])
    return ProductCard.of(view)


@router.post("/events", status_code=204, dependencies=[Depends(rate_limit)], tags=["tracking"])
async def track(event: TrackEvent, c: Container = Depends(get_container)):
    ev = event.sanitized().model_copy(update={"ts": utcnow()})
    await c.repos.events.add(ev)


@router.get("/admin/stats", dependencies=[Depends(require_admin)], tags=["admin"])
async def stats(c: Container = Depends(get_container)):
    return {"events": await c.repos.events.count_by_type()}
