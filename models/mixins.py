"""Shared model properties used across the order module."""


class OrderMixin:
    """Common computed properties for order-type records."""

    @property
    def is_pending(self):
        return self.status == "pending"

    @property
    def is_cancellable(self):
        return self.status in ("pending", "confirmed")

    @property
    def total(self):
        """Net total after platform processing fee (2.9%)."""
        return round(self.total_amount * 0.971, 2)

    @property
    def display_status(self):
        return self.status.replace("_", " ").title()
