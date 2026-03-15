"""
Payment Gateway outcome checks — ground truth verification via the Payment Gateway API.

Each check verifies a condition against the real API (port 8002).
The API reads from the database, so this IS ground truth verification.
The reward system uses these results as the dominant scoring signal (weight 0.60).

Session-aware: when a session_id is provided, the checker sends an
X-Session-ID header so the API routes to the correct isolated database.

Check types:
  - customer_exists     : customer with given email exists
  - customer_name       : customer name matches expected value
  - payment_status      : at least one payment for customer has given status
  - payment_amount      : at least one payment for customer has given amount
  - refund_exists       : at least one refund exists for customer's payments
  - dispute_status      : dispute for customer's payment has given status
  - transfer_exists     : transfer to given destination exists
  - transfer_amount     : transfer to destination has given amount
  - balance_equals      : account balance equals expected amount (cents)
  - balance_gte         : account balance >= expected amount (cents)
  - webhook_received    : at least one webhook with given event_type
  - webhook_count_gte   : total webhook count >= expected

To add a new check type: define _check_{type}(self, check) -> bool
"""

import httpx
from typing import Any, Dict, List, Optional


class PaymentChecker:
    """Verifies outcomes against the Payment Gateway API (ground truth)."""

    def __init__(
        self,
        api_url: str = "http://localhost:8002",
        session_id: Optional[str] = None,
    ):
        headers = {}
        if session_id:
            headers["X-Session-ID"] = session_id

        self._client = httpx.Client(
            base_url=api_url,
            timeout=10.0,
            headers=headers,
        )
        self._session_id = session_id

    def check_all(self, checks: List[Dict[str, Any]]) -> List[bool]:
        """Run all outcome checks, return list of pass/fail."""
        return [self._run_check(c) for c in checks]

    def set_session(self, session_id: str):
        """Update the session ID for concurrent evaluations."""
        self._session_id = session_id
        if session_id:
            self._client.headers["X-Session-ID"] = session_id
        else:
            self._client.headers.pop("X-Session-ID", None)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── Check Dispatcher ──

    def _run_check(self, check: Dict[str, Any]) -> bool:
        check_type = check.get("type", "")
        handler = getattr(self, f"_check_{check_type}", None)
        if not handler:
            raise ValueError(f"Unknown check type: {check_type}")
        try:
            return handler(check)
        except Exception:
            return False

    # ── Check Implementations ──

    def _check_customer_exists(self, check: dict) -> bool:
        """Verify a customer with the given email exists."""
        return self._find_customer_by_email(check["email"]) is not None

    def _check_customer_name(self, check: dict) -> bool:
        """Verify a customer's name matches expected value."""
        customer = self._find_customer_by_email(check["email"])
        if not customer:
            return False
        return customer.get("name") == check["expected_name"]

    def _check_payment_status(self, check: dict) -> bool:
        """Verify at least one payment for this customer has the given status."""
        payments = self._get_payments_for_customer(check["customer_email"])
        return any(p["status"] == check["status"] for p in payments)

    def _check_payment_amount(self, check: dict) -> bool:
        """Verify at least one payment for this customer has the given amount."""
        payments = self._get_payments_for_customer(check["customer_email"])
        expected = check["amount"]
        return any(abs(p["amount"] - expected) < 0.01 for p in payments)

    def _check_refund_exists(self, check: dict) -> bool:
        """Verify at least one refund exists for this customer's payments."""
        payment_ids = self._get_payment_ids_for_customer(check["customer_email"])
        if not payment_ids:
            return False
        refunds = self._get_refunds()
        return any(r["payment_intent_id"] in payment_ids for r in refunds)

    def _check_dispute_status(self, check: dict) -> bool:
        """Verify a dispute for this customer's payment has the given status."""
        payment_ids = self._get_payment_ids_for_customer(check["customer_email"])
        if not payment_ids:
            return False
        disputes = self._get_disputes()
        return any(
            d["payment_intent_id"] in payment_ids and d["status"] == check["status"]
            for d in disputes
        )

    def _check_transfer_exists(self, check: dict) -> bool:
        """Verify a transfer to the given destination exists."""
        transfers = self._get_transfers()
        return any(t["destination"] == check["destination"] for t in transfers)

    def _check_transfer_amount(self, check: dict) -> bool:
        """Verify a transfer to the destination has the expected amount."""
        transfers = self._get_transfers()
        expected = check["amount"]
        return any(
            t["destination"] == check["destination"]
            and abs(t["amount"] - expected) < 0.01
            for t in transfers
        )

    def _check_balance_equals(self, check: dict) -> bool:
        """Verify account balance equals expected amount (in cents)."""
        balance = self._get_balance()
        return abs(balance - check["amount"]) < 0.01

    def _check_balance_gte(self, check: dict) -> bool:
        """Verify account balance >= expected amount (in cents)."""
        balance = self._get_balance()
        return balance >= check["amount"] - 0.01

    def _check_webhook_received(self, check: dict) -> bool:
        """Verify at least one webhook with the given event_type was received."""
        webhooks = self._get_webhooks()
        return any(w["event_type"] == check["event_type"] for w in webhooks)

    def _check_webhook_count_gte(self, check: dict) -> bool:
        """Verify total webhook count >= expected."""
        webhooks = self._get_webhooks()
        return len(webhooks) >= check["count"]

    # ── Helpers ──

    def _get_customers(self) -> list:
        resp = self._client.get("/customers")
        resp.raise_for_status()
        return resp.json().get("customers", [])

    def _get_payments(self) -> list:
        resp = self._client.get("/payments")
        resp.raise_for_status()
        return resp.json().get("payments", [])

    def _get_refunds(self) -> list:
        resp = self._client.get("/refunds")
        resp.raise_for_status()
        return resp.json().get("refunds", [])

    def _get_disputes(self) -> list:
        resp = self._client.get("/disputes")
        resp.raise_for_status()
        return resp.json().get("disputes", [])

    def _get_transfers(self) -> list:
        resp = self._client.get("/transfers")
        resp.raise_for_status()
        return resp.json().get("transfers", [])

    def _get_webhooks(self) -> list:
        resp = self._client.get("/webhooks")
        resp.raise_for_status()
        return resp.json().get("events", [])

    def _get_balance(self) -> float:
        resp = self._client.get("/balance")
        resp.raise_for_status()
        return resp.json().get("balance", 0)

    def _find_customer_by_email(self, email: str):
        customers = self._get_customers()
        return next((c for c in customers if c["email"] == email), None)

    def _get_payments_for_customer(self, email: str) -> list:
        payments = self._get_payments()
        return [p for p in payments if p.get("customer_email") == email]

    def _get_payment_ids_for_customer(self, email: str) -> set:
        payments = self._get_payments_for_customer(email)
        return {p["id"] for p in payments}
