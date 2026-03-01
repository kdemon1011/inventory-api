from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from database import get_db
from schemas.order import OrderCreate, OrderResponse, OrderSummary
from services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    try:
        order = await order_service.create_order(db, data)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    start_date: datetime = None,
    end_date: datetime = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    return await order_service.list_orders(db, start_date, end_date, status)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    order = await order_service.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order not found")
    return order


@router.get("/{order_id}/detail")
async def order_detail(order_id: int, db: AsyncSession = Depends(get_db)):
    detail = await order_service.get_order_detail(db, order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="order not found")
    return detail


@router.get("/{order_id}/summary", response_model=OrderSummary)
async def order_summary(order_id: int, db: AsyncSession = Depends(get_db)):
    summary = await order_service.get_order_summary(db, order_id)
    if not summary:
        raise HTTPException(status_code=404, detail="order not found")
    return summary
