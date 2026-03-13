"""
Stripe Mock HTTP Client — adapter for communicating with the Node.js Stripe mock.

This is the bridge between the Python gateway and the external Stripe-like
service running on port 3001. All payment processing, refunds, disputes,
and transfers go through here.
"""

import logging
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

STRIPE_MOCK_URL = os.getenv("STRIPE_MOCK_URL", "http://localhost:3001")

logger = logging.getLogger(__name__)


class StripeClient:
    """HTTP client for the Stripe mock service."""

    def __init__(self, base_url: str = STRIPE_MOCK_URL):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=15.0)

    # ── Payment Intents ──

    async def create_payment_intent(
        self, amount: float, currency: str, customer_email: str,
        description: Optional[str] = None, metadata: Optional[dict] = None,
    ) -> dict:
        """Create a payment intent on the Stripe mock."""
        payload = {"amount": amount, "currency": currency, "customer_email": customer_email}
        if description:
            payload["description"] = description
        if metadata:
            payload["metadata"] = metadata
        resp = await self._client.post("/v1/payment_intents", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def confirm_payment_intent(self, stripe_pi_id: str) -> dict:
        """Confirm a payment intent on the Stripe mock."""
        resp = await self._client.post(f"/v1/payment_intents/{stripe_pi_id}/confirm")
        resp.raise_for_status()
        return resp.json()

    async def get_payment_intent(self, stripe_pi_id: str) -> dict:
        """Retrieve a payment intent from the Stripe mock."""
        resp = await self._client.get(f"/v1/payment_intents/{stripe_pi_id}")
        resp.raise_for_status()
        return resp.json()

    # ── Refunds ──

    async def create_refund(self, stripe_pi_id: str, amount: Optional[float] = None) -> dict:
        """Create a refund on the Stripe mock."""
        payload = {"payment_intent": stripe_pi_id}
        if amount is not None:
            payload["amount"] = amount
        resp = await self._client.post("/v1/refunds", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ── Disputes ──

    async def create_dispute(
        self, stripe_pi_id: str, amount: float, reason: str = "general",
    ) -> dict:
        """Open a dispute on the Stripe mock."""
        payload = {"payment_intent": stripe_pi_id, "amount": amount, "reason": reason}
        resp = await self._client.post("/v1/disputes", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def resolve_dispute(
        self, stripe_dispute_id: str, evidence: str, accept_loss: bool = False,
    ) -> dict:
        """Submit evidence and close a dispute on the Stripe mock."""
        payload = {"evidence": evidence, "accept_loss": accept_loss}
        resp = await self._client.post(f"/v1/disputes/{stripe_dispute_id}/close", json=payload)
        resp.raise_for_status()
        return resp.json()

    # ── Transfers ──

    async def create_transfer(
        self, amount: float, destination: str, description: Optional[str] = None,
    ) -> dict:
        """Create a transfer/payout on the Stripe mock."""
        payload = {"amount": amount, "destination": destination}
        if description:
            payload["description"] = description
        resp = await self._client.post("/v1/transfers", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self._client.aclose()


# Shared singleton — used by all service modules
stripe_client = StripeClient()
