"""Pydantic schemas for transfer/payout management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateTransferRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Transfer amount in cents")
    destination: str = Field(..., description="Destination account (e.g. 'acct_merchant_001')")
    description: Optional[str] = None


class TransferResponse(BaseModel):
    id: int
    stripe_transfer_id: Optional[str]
    amount: float
    currency: str
    destination: str
    status: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TransferListResponse(BaseModel):
    transfers: list[TransferResponse]
    count: int
