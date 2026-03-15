"""
Refund model — tracks refunds against completed PaymentIntents.

Refunds can be full or partial. Each refund hits the Stripe mock and
records the result. Multiple partial refunds are allowed up to the
original payment amount.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_intent_id = Column(Integer, ForeignKey("payment_intents.id"), nullable=False, index=True)
    stripe_refund_id = Column(String(255), unique=True, nullable=True)
    amount = Column(Float, nullable=False)   # refund amount in cents
    status = Column(String(50), nullable=False, default="pending")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    payment_intent = relationship("PaymentIntent", back_populates="refunds")
