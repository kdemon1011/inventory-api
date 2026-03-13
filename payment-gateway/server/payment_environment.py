"""
Payment Gateway Environment — built on OpenEnv's MCPEnvironment.

Exposes 19 MCP tools covering the full payment lifecycle:
  - Infrastructure: get_session_info
  - Customer management: create, get, list, update
  - Payment intents: create, confirm, get, list, retry
  - Refunds: create, list
  - Disputes: create, resolve, list
  - Transfers: create, list
  - Balance and webhook inspection

Architecture:
    LLM Agent ──WS──► OpenEnv (9002) ──HTTP──► Gateway API (8002) ──HTTP──► Stripe Mock (3001)
"""

import logging
import os
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastmcp import FastMCP

from openenv.core.env_server.mcp_environment import MCPEnvironment
from openenv.core.env_server.types import Action, EnvironmentMetadata, Observation, State

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

PAYMENT_API_URL = os.getenv("PAYMENT_API_URL", "http://localhost:8002")

logger = logging.getLogger(__name__)


class PaymentEnvironment(MCPEnvironment):
    """
    OpenEnv environment for the Payment Gateway.

    19 MCP tools for the full payment lifecycle — customers, payments,
    refunds, disputes, transfers, balance, and webhooks.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        mcp = FastMCP("payment_gateway")

        self._session_id: Optional[str] = None
        self._http_client = httpx.Client(base_url=PAYMENT_API_URL, timeout=30.0)
        self._state = State(episode_id=str(uuid4()), step_count=0)

        # ────────────────────────────────────────
        # Infrastructure Tool
        # ────────────────────────────────────────

        @mcp.tool()
        def get_session_info() -> dict:
            """
            Get the current session information (infrastructure tool).
            Returns session_id for DB isolation in concurrent evaluation mode.
            """
            return {
                "session_id": self._session_id,
                "episode_id": self._state.episode_id,
            }

        # ────────────────────────────────────────
        # Customer Tools
        # ────────────────────────────────────────

        @mcp.tool()
        def create_customer(email: str, name: str, phone: str = "", address: str = "") -> dict:
            """
            Register a new customer in the payment gateway.

            Args:
                email: Customer email (must be unique)
                name: Customer full name
                phone: Optional phone number
                address: Optional address (as a string)

            Returns:
                The created customer record with ID and timestamps.
            """
            payload = {"email": email, "name": name}
            if phone:
                payload["phone"] = phone
            if address:
                payload["address"] = {"line1": address}
            resp = self._http_client.post("/customers", json=payload)
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def get_customer(customer_id: int) -> dict:
            """
            Get a customer's details by their ID.

            Args:
                customer_id: The customer ID

            Returns:
                Customer details (email, name, phone, address, timestamps).
            """
            resp = self._http_client.get(f"/customers/{customer_id}")
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def list_customers() -> dict:
            """
            List all registered customers.

            Returns:
                Object with 'customers' list and 'count'.
            """
            resp = self._http_client.get("/customers")
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def update_customer(customer_id: int, name: str = "", phone: str = "") -> dict:
            """
            Update a customer's details.

            Args:
                customer_id: The customer ID to update
                name: New name (empty = no change)
                phone: New phone (empty = no change)

            Returns:
                Updated customer record.
            """
            payload = {}
            if name:
                payload["name"] = name
            if phone:
                payload["phone"] = phone
            if not payload:
                return {"error": "No fields to update"}
            resp = self._http_client.patch(f"/customers/{customer_id}", json=payload)
            resp.raise_for_status()
            return resp.json()

        # ────────────────────────────────────────
        # Payment Tools
        # ────────────────────────────────────────

        @mcp.tool()
        def create_payment(
            amount: float, currency: str, customer_email: str,
            description: str = "",
        ) -> dict:
            """
            Create a new payment intent for a customer.

            Args:
                amount: Amount in cents (e.g. 5000 = $50.00)
                currency: Three-letter currency code (e.g. "usd")
                customer_email: Customer's email address
                description: Optional payment description

            Returns:
                Created payment intent with ID, status, and Stripe reference.
            """
            payload = {"amount": amount, "currency": currency, "customer_email": customer_email}
            if description:
                payload["description"] = description
            resp = self._http_client.post("/payments", json=payload)
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def confirm_payment(payment_id: int) -> dict:
            """
            Confirm a pending payment intent. The payment must be in 'requires_confirmation' status.

            Args:
                payment_id: The local payment intent ID

            Returns:
                Updated payment with new status (succeeded/failed).
            """
            resp = self._http_client.post(f"/payments/{payment_id}/confirm")
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def get_payment(payment_id: int) -> dict:
            """
            Get details of a specific payment intent.

            Args:
                payment_id: The local payment intent ID

            Returns:
                Payment details (status, amount, customer, timestamps).
            """
            resp = self._http_client.get(f"/payments/{payment_id}")
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def list_payments(status: str = "") -> dict:
            """
            List all payment intents, optionally filtered by status.

            Args:
                status: Filter by status ("succeeded", "failed", "requires_confirmation", "disputed").
                        Leave empty for all.

            Returns:
                Object with 'payments' list and 'count'.
            """
            params = {}
            if status:
                params["status"] = status
            resp = self._http_client.get("/payments", params=params)
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def retry_payment(payment_id: int, amount: float = 0, description: str = "") -> dict:
            """
            Retry a failed payment — creates a new payment intent for the same customer and confirms it.

            Args:
                payment_id: ID of the failed payment to retry
                amount: New amount in cents (0 = use original amount)
                description: Updated description (empty = use original)

            Returns:
                The new (retried) payment intent after confirmation.
            """
            orig_resp = self._http_client.get(f"/payments/{payment_id}")
            orig_resp.raise_for_status()
            original = orig_resp.json()

            new_amount = amount if amount > 0 else original["amount"]
            new_desc = description if description else original.get("description", "")
            payload = {
                "amount": new_amount,
                "currency": original["currency"],
                "customer_email": original["customer_email"],
            }
            if new_desc:
                payload["description"] = new_desc

            create_resp = self._http_client.post("/payments", json=payload)
            create_resp.raise_for_status()
            new_payment = create_resp.json()

            confirm_resp = self._http_client.post(f"/payments/{new_payment['id']}/confirm")
            confirm_resp.raise_for_status()
            return confirm_resp.json()

        # ────────────────────────────────────────
        # Refund Tools
        # ────────────────────────────────────────

        @mcp.tool()
        def create_refund(payment_intent_id: int, amount: float = 0, reason: str = "") -> dict:
            """
            Refund a completed payment (full or partial).

            Args:
                payment_intent_id: ID of the succeeded payment to refund
                amount: Refund amount in cents (0 = full refund)
                reason: Optional reason for the refund

            Returns:
                Created refund with ID, amount, and status.
            """
            payload = {"payment_intent_id": payment_intent_id}
            if amount > 0:
                payload["amount"] = amount
            if reason:
                payload["reason"] = reason
            resp = self._http_client.post("/refunds", json=payload)
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def list_refunds() -> dict:
            """
            List all refunds.

            Returns:
                Object with 'refunds' list and 'count'.
            """
            resp = self._http_client.get("/refunds")
            resp.raise_for_status()
            return resp.json()

        # ────────────────────────────────────────
        # Dispute Tools
        # ────────────────────────────────────────

        @mcp.tool()
        def create_dispute(payment_intent_id: int, reason: str, amount: float = 0) -> dict:
            """
            Open a dispute/chargeback against a succeeded payment.

            Args:
                payment_intent_id: ID of the payment being disputed
                reason: Reason for dispute ("fraudulent", "duplicate", "product_not_received", "other")
                amount: Disputed amount in cents (0 = full payment amount)

            Returns:
                Created dispute with ID, status ("open"), and details.
            """
            payload = {"payment_intent_id": payment_intent_id, "reason": reason}
            if amount > 0:
                payload["amount"] = amount
            resp = self._http_client.post("/disputes", json=payload)
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def resolve_dispute(dispute_id: int, evidence: str, accept_loss: bool = False) -> dict:
            """
            Submit evidence and resolve a dispute.

            Args:
                dispute_id: ID of the open dispute
                evidence: Evidence text (e.g. proof of delivery, receipt details)
                accept_loss: If True, accept the dispute loss. If False, fight it.

            Returns:
                Resolved dispute with final status ("won" or "lost").
            """
            payload = {"evidence": evidence, "accept_loss": accept_loss}
            resp = self._http_client.post(f"/disputes/{dispute_id}/resolve", json=payload)
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def list_disputes(status: str = "") -> dict:
            """
            List all disputes, optionally filtered by status.

            Args:
                status: Filter by status ("open", "won", "lost"). Empty for all.

            Returns:
                Object with 'disputes' list and 'count'.
            """
            params = {}
            if status:
                params["status"] = status
            resp = self._http_client.get("/disputes", params=params)
            resp.raise_for_status()
            return resp.json()

        # ────────────────────────────────────────
        # Transfer Tools
        # ────────────────────────────────────────

        @mcp.tool()
        def create_transfer(amount: float, destination: str, description: str = "") -> dict:
            """
            Transfer funds from the gateway balance to an external destination.

            The transfer amount cannot exceed the available balance
            (payments - refunds - lost disputes - previous transfers).

            Args:
                amount: Transfer amount in cents
                destination: Destination account ID (e.g. "acct_merchant_001")
                description: Optional description

            Returns:
                Created transfer with ID, amount, status.
            """
            payload = {"amount": amount, "destination": destination}
            if description:
                payload["description"] = description
            resp = self._http_client.post("/transfers", json=payload)
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def list_transfers() -> dict:
            """
            List all transfers/payouts.

            Returns:
                Object with 'transfers' list and 'count'.
            """
            resp = self._http_client.get("/transfers")
            resp.raise_for_status()
            return resp.json()

        # ────────────────────────────────────────
        # Balance & Webhook Tools
        # ────────────────────────────────────────

        @mcp.tool()
        def get_balance() -> dict:
            """
            Get the current account balance summary.

            Balance = succeeded payments - refunds - lost disputes - completed transfers.

            Returns:
                Object with balance, total_payments, total_refunds, total_disputes_lost,
                total_transfers, and currency.
            """
            resp = self._http_client.get("/balance")
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def list_webhooks() -> dict:
            """
            List all received webhook events from the Stripe mock.

            Useful for auditing the payment lifecycle and verifying
            that events (payment.succeeded, charge.refunded, dispute.created, etc.)
            were properly delivered.

            Returns:
                Object with 'events' list and 'count'.
            """
            resp = self._http_client.get("/webhooks")
            resp.raise_for_status()
            return resp.json()

        # Pass MCP server to base class
        super().__init__(mcp)

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Observation:
        """Reset the environment — creates a fresh session with an isolated DB."""
        self._session_id = str(uuid4())

        try:
            resp = self._http_client.post(
                "/sessions", params={"session_id": self._session_id}
            )
            resp.raise_for_status()
            logger.info(f"Session created: {self._session_id}")
        except Exception as e:
            logger.warning(f"Failed to create session '{self._session_id}': {e}. Falling back to default DB.")
            self._session_id = None

        if self._session_id:
            self._http_client.headers["X-Session-ID"] = self._session_id
        else:
            self._http_client.headers.pop("X-Session-ID", None)

        self._state = State(
            episode_id=episode_id or self._session_id or str(uuid4()),
            step_count=0,
        )

        return Observation(
            done=False,
            reward=0.0,
            metadata={"status": "ready", "session_id": self._session_id},
        )

    def _step_impl(self, action: Action, timeout_s: Optional[float] = None, **kwargs: Any) -> Observation:
        return Observation(
            done=False, reward=0.0,
            metadata={"error": f"Unknown action type: {type(action).__name__}. Use ListToolsAction or CallToolAction."},
        )

    def step(self, action: Action, timeout_s: Optional[float] = None, **kwargs: Any) -> Observation:
        self._state.step_count += 1
        return super().step(action, timeout_s=timeout_s, **kwargs)

    @property
    def state(self) -> State:
        return self._state

    def get_metadata(self) -> EnvironmentMetadata:
        readme_content = None
        try:
            readme_path = os.path.join(os.path.dirname(__file__), "..", "README.md")
            if os.path.exists(readme_path):
                with open(readme_path, "r") as f:
                    readme_content = f.read()
        except Exception:
            pass

        return EnvironmentMetadata(
            name="payment_gateway",
            description=(
                "Payment Gateway — 19 MCP tools for the full payment lifecycle: "
                "customer management, payment processing, refunds, disputes/chargebacks, "
                "transfers/payouts, balance tracking, and webhook auditing. "
                "Integrates with a Stripe-like mock service (Node.js). "
                "Supports concurrent sessions with per-session DB isolation."
            ),
            version="0.1.0",
            author="RL Gyms Team",
            readme_content=readme_content,
            documentation_url="payment-gateway/README.md",
        )

    def close(self) -> None:
        if self._session_id:
            try:
                self._http_client.delete(f"/sessions/{self._session_id}")
                logger.info(f"Session deleted: {self._session_id}")
            except Exception as e:
                logger.warning(f"Failed to delete session: {e}")
            self._session_id = None

        self._http_client.headers.pop("X-Session-ID", None)
        self._http_client.close()
        super().close()
