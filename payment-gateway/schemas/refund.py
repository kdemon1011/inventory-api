"""Pydantic schemas for refund requests and responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateRefundRequest(BaseModel):
    payment_intent_id: int = Field(..., description="ID of the payment to refund")
    amount: Optional[float] = Field(None, gt=0, description="Partial refund amount in cents. Omit for full refund.")
    reason: Optional[str] = None


class RefundResponse(BaseModel):
    id: int
    payment_intent_id: int
    stripe_refund_id: Optional[str]
    amount: float
    status: str
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class RefundListResponse(BaseModel):
    refunds: list[RefundResponse]
    count: int
