"""
Transfer/payout endpoints — move funds from gateway balance to external accounts.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.transfer import CreateTransferRequest, TransferResponse, TransferListResponse
from services import transfer_service

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("", response_model=TransferResponse, status_code=201)
async def create_transfer(req: CreateTransferRequest, db: AsyncSession = Depends(get_db)):
    try:
        transfer = await transfer_service.create_transfer(
            db=db,
            amount=req.amount, destination=req.destination,
            description=req.description,
        )
        return transfer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=TransferListResponse)
async def list_transfers(db: AsyncSession = Depends(get_db)):
    transfers = await transfer_service.list_transfers(db=db)
    return TransferListResponse(transfers=transfers, count=len(transfers))
