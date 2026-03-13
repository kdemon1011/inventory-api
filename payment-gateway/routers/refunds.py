"""
Refund endpoints — create and list refunds against completed payments.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, get_session_id
from schemas.refund import CreateRefundRequest, RefundResponse, RefundListResponse
from services import refund_service

router = APIRouter(prefix="/refunds", tags=["refunds"])


@router.post("", response_model=RefundResponse, status_code=201)
async def create_refund(req: CreateRefundRequest, db: AsyncSession = Depends(get_db), session_id: Optional[str] = Depends(get_session_id)):
    try:
        refund = await refund_service.create_refund(
            db=db,
            payment_intent_id=req.payment_intent_id,
            amount=req.amount, reason=req.reason,
            session_id=session_id,
        )
        return refund
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=RefundListResponse)
async def list_refunds(db: AsyncSession = Depends(get_db)):
    refunds = await refund_service.list_refunds(db=db)
    return RefundListResponse(refunds=refunds, count=len(refunds))
