"""
Payment endpoints — create, confirm, list, and retrieve payment intents.

The agent (via OpenEnv tools) drives the payment lifecycle:
  create → confirm → check status
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.payment import CreatePaymentRequest, PaymentResponse, PaymentListResponse
from services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment(req: CreatePaymentRequest, db: AsyncSession = Depends(get_db)):
    payment = await payment_service.create_payment(
        db=db,
        amount=req.amount, currency=req.currency,
        customer_email=req.customer_email,
        description=req.description, metadata=req.metadata,
    )
    return payment


@router.post("/{payment_id}/confirm", response_model=PaymentResponse)
async def confirm_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    try:
        payment = await payment_service.confirm_payment(db=db, payment_id=payment_id)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=PaymentListResponse)
async def list_payments(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    payments = await payment_service.list_payments(db=db, status=status)
    return PaymentListResponse(payments=payments, count=len(payments))


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    payment = await payment_service.get_payment(db=db, payment_id=payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
    return payment
