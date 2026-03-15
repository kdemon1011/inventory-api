"""Pydantic schemas for payment intent requests and responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreatePaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in cents (e.g. 5000 = $50.00)")
    currency: str = Field(default="usd", max_length=3)
    customer_email: str = Field(..., description="Customer email address")
    description: Optional[str] = None
    metadata: Optional[dict] = None


class PaymentResponse(BaseModel):
    id: int
    stripe_payment_intent_id: Optional[str]
    amount: float
    currency: str
    status: str
    customer_email: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentListResponse(BaseModel):
    payments: list[PaymentResponse]
    count: int
