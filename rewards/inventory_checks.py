"""
Inventory-specific outcome checks.

Each check verifies a condition against the real Inventory API.
The API reads from the database, so this IS ground truth verification.

Check types:
  - product_exists      : product with given SKU exists
  - product_field       : product field matches expected value
  - order_exists        : order for given customer email exists
  - order_has_items     : order contains expected number of items
  - stock_decreased     : product stock went down by expected amount

To add a new check: define _check_{type}(self, check) -> bool
"""

import httpx
from typing import Any, Dict, List


class InventoryChecker:
    """Verifies outcomes against the Inventory API (ground truth)."""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self._client = httpx.Client(base_url=api_url, timeout=10.0)

    def check_all(self, checks: List[Dict[str, Any]]) -> List[bool]:
        """Run all outcome checks, return list of pass/fail."""
        return [self._run_check(c) for c in checks]

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

    def _check_product_exists(self, check: dict) -> bool:
        """Verify a product with the given SKU exists."""
        products = self._get_products()
        return any(p["sku"] == check["sku"] for p in products)

    def _check_product_field(self, check: dict) -> bool:
        """Verify a product field has the expected value."""
        product = self._find_product_by_sku(check["sku"])
        if not product:
            return False
        actual = product.get(check["field"])
        expected = check["value"]
        # Float comparison with tolerance
        if isinstance(expected, float) and isinstance(actual, (int, float)):
            return abs(float(actual) - expected) < 0.01
        return actual == expected

    def _check_order_exists(self, check: dict) -> bool:
        """Verify an order exists for the given customer email."""
        orders = self._get_orders()
        return any(o.get("customer_email") == check["customer_email"] for o in orders)

    def _check_order_has_items(self, check: dict) -> bool:
        """Verify an order has the expected number of item lines."""
        order = self._find_order_by_email(check["customer_email"])
        if not order:
            return False
        order_id = order["id"]
        try:
            resp = self._client.get(f"/orders/{order_id}/detail")
            detail = resp.json()
            items = detail.get("items", [])
            return len(items) == check["expected_count"]
        except Exception:
            return False

    def _check_stock_quantity(self, check: dict) -> bool:
        """Verify a product's stock quantity matches expected value."""
        product = self._find_product_by_sku(check["sku"])
        if not product:
            return False
        return product.get("stock_quantity") == check["value"]

    # ── Helpers ──

    def _get_products(self) -> list:
        resp = self._client.get("/products", params={"active_only": False})
        resp.raise_for_status()
        return resp.json()

    def _get_orders(self) -> list:
        resp = self._client.get("/orders")
        resp.raise_for_status()
        return resp.json()

    def _find_product_by_sku(self, sku: str):
        products = self._get_products()
        return next((p for p in products if p["sku"] == sku), None)

    def _find_order_by_email(self, email: str):
        orders = self._get_orders()
        return next((o for o in orders if o.get("customer_email") == email), None)
