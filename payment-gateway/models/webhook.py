"""
WebhookEvent model — logs incoming webhook events from the Stripe mock.

The Stripe mock POSTs events (e.g. payment_intent.succeeded) to the
gateway's /webhooks/receive endpoint. Each event is stored for
auditing and can be used to verify async payment lifecycle updates.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from database import Base


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stripe_event_id = Column(String(255), unique=True, nullable=True, index=True)
    event_type = Column(String(100), nullable=False)       # e.g. "payment_intent.succeeded"
    payload = Column(Text, nullable=False)                  # full JSON payload
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
