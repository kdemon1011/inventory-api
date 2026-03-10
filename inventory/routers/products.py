from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas.product import ProductCreate, ProductUpdate, ProductResponse
from services import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    try:
        product = await product_service.create_product(db, data)
        return product
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[ProductResponse])
async def list_products(
    active_only: bool = True, db: AsyncSession = Depends(get_db)
):
    return await product_service.get_products(db, active_only=active_only)


@router.get("/search", response_model=list[ProductResponse])
async def search_products(q: str = Query(...), db: AsyncSession = Depends(get_db)):
    return await product_service.search_products(db, q)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int, data: ProductUpdate, db: AsyncSession = Depends(get_db)
):
    product = await product_service.update_product(db, product_id, data)
    if not product:
        raise HTTPException(status_code=404, detail="product not found")
    return product
