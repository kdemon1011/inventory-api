"""
Dispute endpoints — open, resolve, and list payment disputes/chargebacks.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, get_session_id
from schemas.dispute import (
    CreateDisputeRequest,
    ResolveDisputeRequest,
    DisputeResponse,
    DisputeListResponse,
)
from services import dispute_service

router = APIRouter(prefix="/disputes", tags=["disputes"])


@router.post("", response_model=DisputeResponse, status_code=201)
async def create_dispute(req: CreateDisputeRequest, db: AsyncSession = Depends(get_db), session_id: Optional[str] = Depends(get_session_id)):
    try:
        dispute = await dispute_service.create_dispute(
            db=db,
            payment_intent_id=req.payment_intent_id,
            reason=req.reason, amount=req.amount,
            session_id=session_id,
        )
        return dispute
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{dispute_id}/resolve", response_model=DisputeResponse)
async def resolve_dispute(
    dispute_id: int, req: ResolveDisputeRequest, db: AsyncSession = Depends(get_db), session_id: Optional[str] = Depends(get_session_id)
):
    try:
        dispute = await dispute_service.resolve_dispute(
            db=db,
            dispute_id=dispute_id,
            evidence=req.evidence, accept_loss=req.accept_loss,
            session_id=session_id,
        )
        return dispute
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=DisputeListResponse)
async def list_disputes(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    disputes = await dispute_service.list_disputes(db=db, status=status)
    return DisputeListResponse(disputes=disputes, count=len(disputes))
