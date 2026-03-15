"""Pydantic schemas for dispute/chargeback management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateDisputeRequest(BaseModel):
    payment_intent_id: int = Field(..., description="ID of the payment being disputed")
    reason: str = Field(..., description="Dispute reason: fraudulent, duplicate, product_not_received, other")
    amount: Optional[float] = Field(None, description="Disputed amount in cents. Omit for full amount.")


class ResolveDisputeRequest(BaseModel):
    evidence: str = Field(..., description="Evidence to submit (e.g. proof of delivery, receipt)")
    accept_loss: bool = Field(default=False, description="If True, accept the dispute (lose). If False, fight it.")


class DisputeResponse(BaseModel):
    id: int
    payment_intent_id: int
    stripe_dispute_id: Optional[str]
    amount: float
    currency: str
    status: str
    reason: Optional[str]
    evidence: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


class DisputeListResponse(BaseModel):
    disputes: list[DisputeResponse]
    count: int
