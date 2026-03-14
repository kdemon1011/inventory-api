"""
Browser Gym — ground truth verification against the Express API (port 8003).

Each check queries the internal verification endpoints (no auth required)
to confirm the database state matches expected outcomes.

Session-aware: sends X-Session-ID header so the Express server routes
to the correct per-session SQLite database.

Check types (16):
  user_exists        — user with given email exists
  user_field         — user field (name, email, address) matches value
  order_exists       — at least one order exists for user email
  order_count        — exact number of orders for user email
  order_status       — order at index has expected status (0=latest)
  order_total        — order total matches (float, ±0.01 tolerance)
  order_discount     — order discount matches (float, ±0.01 tolerance)
  order_coupon       — order coupon_code matches
  order_item_count   — order has expected number of line items
  order_shipping     — order shipping field matches expected value
  cart_count         — user's cart has expected item count
  wishlist_count     — user's wishlist has expected item count
  product_stock      — product stock equals expected value
  review_exists      — review by user on product exists
  review_rating      — review rating matches expected value
  contact_exists     — contact form submission with email exists
"""

import httpx
from typing import Any, Dict, List, Optional


class BrowserChecker:
    """Verifies outcomes against the Browser Gym Express API (ground truth)."""

    def __init__(
        self,
        api_url: str = "http://localhost:8003",
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

    def check_all(self, checks: List[Dict[str, Any]]) -> List[bool]:
        """Run all outcome checks, return list of pass/fail."""
        return [self._run_check(c) for c in checks]

    def set_session(self, session_id: str):
        """Update the session ID for concurrent evaluations."""
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

    # ── User Checks ──

    def _check_user_exists(self, check: dict) -> bool:
        resp = self._client.get("/api/internal/user", params={"email": check["email"]})
        return resp.status_code == 200

    def _check_user_field(self, check: dict) -> bool:
        resp = self._client.get("/api/internal/user", params={"email": check["email"]})
        if resp.status_code != 200:
            return False
        user = resp.json()
        actual = user.get(check["field"])
        expected = check["value"]
        if isinstance(expected, bool):
            return actual == expected
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            return abs(float(actual) - float(expected)) < 0.01
        return str(actual) == str(expected)

    # ── Order Checks ──

    def _get_orders(self, email: str) -> list:
        resp = self._client.get("/api/internal/orders", params={"email": email})
        if resp.status_code != 200:
            return []
        return resp.json().get("orders", [])

    def _get_order_at_index(self, email: str, index: int):
        """Get order at index (0 = latest, 1 = second latest, etc.)."""
        orders = self._get_orders(email)
        if index < len(orders):
            return orders[index]
        return None

    def _check_order_exists(self, check: dict) -> bool:
        orders = self._get_orders(check["email"])
        return len(orders) > 0

    def _check_order_count(self, check: dict) -> bool:
        orders = self._get_orders(check["email"])
        return len(orders) == check["expected"]

    def _check_order_status(self, check: dict) -> bool:
        order = self._get_order_at_index(check["email"], check.get("order_index", 0))
        if not order:
            return False
        return order.get("status") == check["value"]

    def _check_order_total(self, check: dict) -> bool:
        order = self._get_order_at_index(check["email"], check.get("order_index", 0))
        if not order:
            return False
        actual = order.get("total", 0)
        expected = check["value"]
        return abs(float(actual) - float(expected)) < 0.01

    def _check_order_discount(self, check: dict) -> bool:
        order = self._get_order_at_index(check["email"], check.get("order_index", 0))
        if not order:
            return False
        actual = order.get("discount", 0)
        expected = check["value"]
        return abs(float(actual) - float(expected)) < 0.01

    def _check_order_coupon(self, check: dict) -> bool:
        order = self._get_order_at_index(check["email"], check.get("order_index", 0))
        if not order:
            return False
        return order.get("coupon_code") == check["value"]

    def _check_order_item_count(self, check: dict) -> bool:
        order = self._get_order_at_index(check["email"], check.get("order_index", 0))
        if not order:
            return False
        items = order.get("items", [])
        return len(items) == check["expected"]

    def _check_order_shipping(self, check: dict) -> bool:
        order = self._get_order_at_index(check["email"], check.get("order_index", 0))
        if not order:
            return False
        actual = order.get(check["field"], "")
        return str(actual) == str(check["value"])

    # ── Cart / Wishlist Checks ──

    def _check_cart_count(self, check: dict) -> bool:
        resp = self._client.get("/api/internal/cart", params={"email": check["email"]})
        if resp.status_code != 200:
            return False
        return resp.json().get("count", -1) == check["expected"]

    def _check_wishlist_count(self, check: dict) -> bool:
        resp = self._client.get("/api/internal/wishlist", params={"email": check["email"]})
        if resp.status_code != 200:
            return False
        return resp.json().get("count", -1) == check["expected"]

    # ── Product Checks ──

    def _check_product_stock(self, check: dict) -> bool:
        resp = self._client.get(f"/api/products/{check['product_id']}")
        if resp.status_code != 200:
            return False
        product = resp.json()
        return product.get("stock") == check["value"]

    # ── Review Checks ──

    def _check_review_exists(self, check: dict) -> bool:
        params = {"email": check["email"]}
        if "product_id" in check:
            params["product_id"] = check["product_id"]
        resp = self._client.get("/api/internal/reviews", params=params)
        if resp.status_code != 200:
            return False
        reviews = resp.json().get("reviews", [])
        return len(reviews) > 0

    def _check_review_rating(self, check: dict) -> bool:
        params = {"email": check["email"]}
        if "product_id" in check:
            params["product_id"] = check["product_id"]
        resp = self._client.get("/api/internal/reviews", params=params)
        if resp.status_code != 200:
            return False
        reviews = resp.json().get("reviews", [])
        if not reviews:
            return False
        return reviews[0].get("rating") == check["value"]

    # ── Contact Checks ──

    def _check_contact_exists(self, check: dict) -> bool:
        resp = self._client.get("/api/internal/contacts", params={"email": check["email"]})
        if resp.status_code != 200:
            return False
        contacts = resp.json().get("contacts", [])
        return len(contacts) > 0
