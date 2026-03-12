"""
Inventory Clone Environment — built on OpenEnv's MCPEnvironment.

This is a simplified clone of the Inventory gym, created via:
    openenv init inventory_clone

Then customized from the default Gymnasium-style template to use
the MCP-tool pattern (MCPEnvironment + FastMCP).

Architecture (single-process, in-memory):
    ┌─────────────┐  WebSocket   ┌──────────────────────────┐
    │  LLM Agent  │ ──────────► │  THIS ENVIRONMENT        │
    │  (run_eval) │ ◄────────── │  (OpenEnv, port 9000)    │
    └─────────────┘              │  In-memory data store    │
                                 └──────────────────────────┘

Unlike the full Inventory gym (which has a separate FastAPI backend
on port 8000), this clone stores data in-memory using Python dicts.
This demonstrates the MCP-tool pattern without external dependencies.
"""

from typing import Any, Optional
from uuid import uuid4

from fastmcp import FastMCP

from openenv.core.env_server.mcp_environment import MCPEnvironment
from openenv.core.env_server.types import Action, Observation, State


class InventoryCloneEnvironment(MCPEnvironment):
    """
    Simplified inventory environment using in-memory storage.

    Demonstrates the MCP-tool pattern:
    - Inherits from MCPEnvironment (not Environment)
    - Defines tools using @mcp.tool() decorators
    - Tools operate on an in-memory dict instead of a real database
    - Agent discovers tools via list_tools(), calls via call_tool()
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        """Initialize the environment with FastMCP tools and in-memory store."""

        mcp = FastMCP("inventory_clone_env")

        # In-memory data store (replaces the real database)
        self._products: dict[int, dict] = {}
        self._orders: dict[int, dict] = {}
        self._next_product_id = 1
        self._next_order_id = 1

        # Episode tracking
        self._state = State(episode_id=str(uuid4()), step_count=0)

        # ── MCP Tools ──

        @mcp.tool()
        def create_product(
            name: str, sku: str, price: float,
            description: str = "", stock_quantity: int = 0
        ) -> dict:
            """
            Create a new product in the inventory.

            Args:
                name: Product name (e.g., "Wireless Mouse")
                sku: Stock Keeping Unit — unique identifier (e.g., "WM-001")
                price: Product price (must be > 0)
                description: Optional product description
                stock_quantity: Initial stock count (default: 0)

            Returns:
                The created product with its ID.
            """
            if price <= 0:
                raise ValueError("Price must be greater than 0")

            # Check for duplicate SKU
            for p in self._products.values():
                if p["sku"] == sku:
                    raise ValueError(f"Product with SKU '{sku}' already exists")

            product_id = self._next_product_id
            self._next_product_id += 1
            product = {
                "id": product_id,
                "name": name,
                "sku": sku,
                "price": price,
                "description": description,
                "stock_quantity": stock_quantity,
                "is_active": True,
            }
            self._products[product_id] = product
            return product

        @mcp.tool()
        def list_products(active_only: bool = True) -> list:
            """
            List all products in the inventory.

            Args:
                active_only: If True, only return active products (default: True)

            Returns:
                List of product objects.
            """
            products = list(self._products.values())
            if active_only:
                products = [p for p in products if p.get("is_active", True)]
            return products

        @mcp.tool()
        def get_product(product_id: int) -> dict:
            """
            Get details of a specific product by its ID.

            Args:
                product_id: The numeric ID of the product

            Returns:
                Product details.
            """
            if product_id not in self._products:
                raise ValueError(f"Product {product_id} not found")
            return self._products[product_id]

        @mcp.tool()
        def update_product(
            product_id: int,
            name: str = None,
            price: float = None,
            stock_quantity: int = None,
            is_active: bool = None,
        ) -> dict:
            """
            Update an existing product's details.

            Args:
                product_id: The numeric ID of the product to update
                name: New product name (optional)
                price: New price (optional)
                stock_quantity: New stock count (optional)
                is_active: Whether the product is active (optional)

            Returns:
                The updated product object.
            """
            if product_id not in self._products:
                raise ValueError(f"Product {product_id} not found")

            product = self._products[product_id]
            if name is not None:
                product["name"] = name
            if price is not None:
                product["price"] = price
            if stock_quantity is not None:
                product["stock_quantity"] = stock_quantity
            if is_active is not None:
                product["is_active"] = is_active

            return product

        @mcp.tool()
        def create_order(
            customer_name: str,
            items: list,
        ) -> dict:
            """
            Create a new order.

            Args:
                customer_name: Name of the customer
                items: List of items, each with 'product_id' and 'quantity'
                       Example: [{"product_id": 1, "quantity": 2}]

            Returns:
                The created order with ID and total amount.
            """
            total = 0.0
            order_items = []
            for item in items:
                pid = item["product_id"]
                qty = item["quantity"]
                if pid not in self._products:
                    raise ValueError(f"Product {pid} not found")
                product = self._products[pid]
                if product["stock_quantity"] < qty:
                    raise ValueError(
                        f"Insufficient stock for product {pid}: "
                        f"requested {qty}, available {product['stock_quantity']}"
                    )
                line_total = product["price"] * qty
                total += line_total
                order_items.append({
                    "product_id": pid,
                    "product_name": product["name"],
                    "quantity": qty,
                    "unit_price": product["price"],
                    "line_total": line_total,
                })
                # Deduct stock
                product["stock_quantity"] -= qty

            order_id = self._next_order_id
            self._next_order_id += 1
            order = {
                "id": order_id,
                "customer_name": customer_name,
                "items": order_items,
                "total_amount": round(total, 2),
                "status": "pending",
            }
            self._orders[order_id] = order
            return order

        @mcp.tool()
        def list_orders(status: str = None) -> list:
            """
            List all orders, optionally filtered by status.

            Args:
                status: Filter by order status (e.g., "pending", "completed")

            Returns:
                List of order objects.
            """
            orders = list(self._orders.values())
            if status is not None:
                orders = [o for o in orders if o["status"] == status]
            return orders

        @mcp.tool()
        def get_order(order_id: int) -> dict:
            """
            Get details of a specific order by its ID.

            Args:
                order_id: The numeric ID of the order

            Returns:
                Order details including items, total, status.
            """
            if order_id not in self._orders:
                raise ValueError(f"Order {order_id} not found")
            return self._orders[order_id]

        # Pass MCP server to base class — MCPEnvironment auto-discovers
        # all @mcp.tool() functions and exposes them via list_tools() / call_tool()
        super().__init__(mcp)

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Observation:
        """
        Reset the environment for a new episode.

        Clears in-memory data and resets counters.
        """
        self._products.clear()
        self._orders.clear()
        self._next_product_id = 1
        self._next_order_id = 1
        self._state = State(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
        )
        return Observation(
            done=False,
            reward=0.0,
            metadata={"status": "ready", "tools_available": 7},
        )

    def _step_impl(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Handle non-MCP actions (fallback for unknown action types)."""
        return Observation(
            done=False,
            reward=0.0,
            metadata={
                "error": f"Unknown action type: {type(action).__name__}. "
                "Use ListToolsAction or CallToolAction."
            },
        )

    def step(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Execute a step — delegates MCP actions to the base class."""
        self._state.step_count += 1
        return super().step(action, timeout_s=timeout_s, **kwargs)

    @property
    def state(self) -> State:
        """Get the current environment state."""
        return self._state

    def close(self) -> None:
        """Clean up resources."""
        super().close()
