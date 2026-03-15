"""
PaymentIntent model — the core entity of the payment gateway.

A PaymentIntent represents a customer's intent to pay. It flows through
a lifecycle: created → requires_confirmation → succeeded / failed.
The gateway creates these locally and mirrors state from the Stripe mock.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=True, index=True)
    amount = Column(Float, nullable=False)                     # in cents (e.g. 5000 = $50.00)
    currency = Column(String(3), nullable=False, default="usd")
    status = Column(String(50), nullable=False, default="requires_confirmation")
    customer_email = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)                # JSON string for arbitrary metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to refunds
    refunds = relationship("Refund", back_populates="payment_intent", lazy="selectin")
