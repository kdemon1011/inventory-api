"""
Inventory Management Environment — built on OpenEnv's MCPEnvironment.

This environment wraps the existing Inventory FastAPI app using OpenEnv's
real framework. Instead of building custom reset/step/state logic, we:

1. Inherit from MCPEnvironment (OpenEnv's base class for tool-based envs)
2. Define tools using FastMCP decorators (@mcp.tool())
3. OpenEnv auto-discovers these tools and handles the Gym-style API

Each tool maps to an operation on the Inventory API (running on port 8000).
The LLM agent discovers tools via list_tools(), then calls them via env.step().

Concurrent Sessions:
    This environment sets SUPPORTS_CONCURRENT_SESSIONS = True, allowing
    multiple agents to evaluate simultaneously. Each session creates an
    isolated SQLite database via the API's session management endpoints
    (POST /sessions). All tool HTTP calls include an X-Session-ID header
    to route to the correct isolated DB.

Architecture:
    ┌─────────────┐  WebSocket   ┌──────────────────────┐  HTTP    ┌──────────────┐
    │  LLM Agent  │ ──────────► │  THIS ENVIRONMENT    │ ───────► │ Inventory API│
    │  (run_eval) │ ◄────────── │  (OpenEnv, port 9000)│ ◄─────── │ (port 8000)  │
    └─────────────┘              └──────────────────────┘          └──────────────┘
        Uses MCPToolClient         Inherits MCPEnvironment           FastAPI + SQLite
                                   Session-scoped HTTP calls         Session-scoped DBs
"""

import logging
import os
import sys
from typing import Any, Optional
from uuid import uuid4

import httpx
from fastmcp import FastMCP

# ── OpenEnv Imports (the REAL library) ──
from openenv.core.env_server.mcp_environment import MCPEnvironment
from openenv.core.env_server.types import Action, EnvironmentMetadata, Observation, State

# Load .env from the gym root (one level up from server/)
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

INVENTORY_API_URL = os.getenv("INVENTORY_API_URL", "http://localhost:8000")

logger = logging.getLogger(__name__)


class InventoryEnvironment(MCPEnvironment):
    """
    OpenEnv environment for the Inventory Management API.

    This class:
    - Inherits from MCPEnvironment (OpenEnv's base class)
    - Defines 10 tools using FastMCP decorators
    - Each tool calls the real Inventory API via HTTP
    - Tracks episode state (step count, reward)
    - Supports concurrent sessions via session-scoped DB isolation

    The AI agent interacts with this via:
      1. list_tools()  → discovers available tools
      2. call_tool("create_product", name="Mouse", sku="M1", price=9.99)
      3. OpenEnv handles all the WebSocket/HTTP plumbing automatically

    Concurrent session support:
      - SUPPORTS_CONCURRENT_SESSIONS = True allows multiple WebSocket sessions
      - Each reset() creates a new session ID → isolated DB
      - All HTTP calls include X-Session-ID header for DB routing
      - close() deletes the session and cleans up the DB
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        """Initialize the environment with FastMCP tools."""

        # Create the MCP server — this is OpenEnv's tool registry
        mcp = FastMCP("inventory_env")

        # Session ID for DB isolation (set during reset)
        self._session_id: Optional[str] = None

        # HTTP client for calling the real Inventory API
        # Headers are updated with X-Session-ID on reset()
        self._http_client = httpx.Client(
            base_url=INVENTORY_API_URL, timeout=30.0
        )

        # Episode tracking
        self._state = State(episode_id=str(uuid4()), step_count=0)

        # ────────────────────────────────────────────────
        # Define all tools using FastMCP decorators
        # These are auto-discovered by OpenEnv's MCPEnvironment
        # ────────────────────────────────────────────────

        @mcp.tool()
        def get_session_info() -> dict:
            """
            Get the current session information.

            Returns the session_id used for database isolation in concurrent
            evaluation mode. The agent runner calls this after reset() to
            route ground truth checks to the correct session database.

            Returns:
                Dict with session_id (or null if no session is active)
            """
            return {
                "session_id": self._session_id,
                "episode_id": self._state.episode_id,
            }

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
                The created product with its ID, timestamps, etc.
            """
            resp = self._http_client.post("/products", json={
                "name": name, "sku": sku, "price": price,
                "description": description, "stock_quantity": stock_quantity
            })
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def list_products(active_only: bool = True) -> list:
            """
            List all products in the inventory.

            Args:
                active_only: If True, only return active products (default: True)

            Returns:
                List of product objects
            """
            resp = self._http_client.get(
                "/products", params={"active_only": active_only}
            )
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def get_product(product_id: int) -> dict:
            """
            Get details of a specific product by its ID.

            Args:
                product_id: The numeric ID of the product

            Returns:
                Product details including name, sku, price, stock, etc.
            """
            resp = self._http_client.get(f"/products/{product_id}")
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def search_products(query: str) -> list:
            """
            Search for products by name or description.

            Args:
                query: Search term to match against product name/description

            Returns:
                List of matching product objects
            """
            resp = self._http_client.get("/products/search", params={"q": query})
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def update_product(
            product_id: int,
            name: str = None,
            description: str = None,
            price: float = None,
            stock_quantity: int = None,
            is_active: bool = None,
        ) -> dict:
            """
            Update an existing product's details.

            Args:
                product_id: The numeric ID of the product to update
                name: New product name (optional)
                description: New description (optional)
                price: New price (optional)
                stock_quantity: New stock count (optional)
                is_active: Whether the product is active (optional)

            Returns:
                The updated product object
            """
            update_data = {}
            if name is not None:
                update_data["name"] = name
            if description is not None:
                update_data["description"] = description
            if price is not None:
                update_data["price"] = price
            if stock_quantity is not None:
                update_data["stock_quantity"] = stock_quantity
            if is_active is not None:
                update_data["is_active"] = is_active

            resp = self._http_client.patch(
                f"/products/{product_id}", json=update_data
            )
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def create_order(
            customer_name: str,
            customer_email: str,
            items: list,
        ) -> dict:
            """
            Create a new order.

            Args:
                customer_name: Name of the customer placing the order
                customer_email: Customer's email address
                items: List of order items, each with 'product_id' and 'quantity'
                       Example: [{"product_id": 1, "quantity": 2}]

            Returns:
                The created order with ID, total amount, status, etc.
            """
            resp = self._http_client.post("/orders", json={
                "customer_name": customer_name,
                "customer_email": customer_email,
                "items": items,
            })
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def list_orders(
            status: str = None,
        ) -> list:
            """
            List all orders, optionally filtered by status.

            Args:
                status: Filter by order status (e.g., "pending", "completed")

            Returns:
                List of order objects
            """
            params = {}
            if status is not None:
                params["status"] = status
            resp = self._http_client.get("/orders", params=params)
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def get_order(order_id: int) -> dict:
            """
            Get details of a specific order by its ID.

            Args:
                order_id: The numeric ID of the order

            Returns:
                Order details including items, total, status, etc.
            """
            resp = self._http_client.get(f"/orders/{order_id}")
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def get_order_detail(order_id: int) -> dict:
            """
            Get full detail of an order including item breakdown.

            Args:
                order_id: The numeric ID of the order

            Returns:
                Detailed order info with individual item details
            """
            resp = self._http_client.get(f"/orders/{order_id}/detail")
            resp.raise_for_status()
            return resp.json()

        @mcp.tool()
        def get_order_summary(order_id: int) -> dict:
            """
            Get a summary of an order (customer, total, item count, status).

            Args:
                order_id: The numeric ID of the order

            Returns:
                Order summary with customer_name, total, item_count, status
            """
            resp = self._http_client.get(f"/orders/{order_id}/summary")
            resp.raise_for_status()
            return resp.json()

        # ── Pass MCP server to the base class ──
        # This is the KEY line — MCPEnvironment auto-discovers all @mcp.tool()
        # functions and makes them available via list_tools() / call_tool()
        super().__init__(mcp)

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Observation:
        """
        Reset the environment for a new episode.

        Creates a new session with an isolated database via the API.
        All subsequent tool calls will use this session's DB.

        Returns:
            Observation with done=False, indicating the episode has started.
        """
        # Generate a unique session ID for DB isolation
        self._session_id = str(uuid4())

        # Create the isolated session DB via the API
        try:
            resp = self._http_client.post(
                "/sessions",
                params={"session_id": self._session_id},
            )
            resp.raise_for_status()
            logger.info(f"Session created: {self._session_id}")
        except Exception as e:
            logger.warning(
                f"Failed to create session '{self._session_id}': {e}. "
                "Falling back to default DB."
            )
            self._session_id = None

        # Set the session header on the HTTP client for all subsequent calls
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
            metadata={
                "status": "ready",
                "session_id": self._session_id,
            },
        )

    def _step_impl(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """
        Handle non-MCP actions (fallback).

        MCPEnvironment routes ListToolsAction and CallToolAction automatically.
        This method is only called for unknown/unsupported action types.
        """
        return Observation(
            done=False,
            reward=0.0,
            metadata={
                "error": f"Unknown action type: {type(action).__name__}. "
                "Use ListToolsAction or CallToolAction for interacting with this environment."
            },
        )

    def step(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """
        Execute a step in the environment.

        Delegates MCP actions (list_tools, call_tool) to the base class.
        Tracks step count and action history.
        """
        self._state.step_count += 1
        return super().step(action, timeout_s=timeout_s, **kwargs)

    @property
    def state(self) -> State:
        """Get the current environment state."""
        return self._state

    def get_metadata(self) -> EnvironmentMetadata:
        """
        Return rich metadata for the OpenEnv Web UI and AutoEnv discovery.

        This overrides the default get_metadata() which only returns
        the class name. Provides human-readable description, version,
        and documentation links.
        """
        readme_content = None
        try:
            readme_path = os.path.join(
                os.path.dirname(__file__), "..", "README.md"
            )
            if os.path.exists(readme_path):
                with open(readme_path, "r") as f:
                    readme_content = f.read()
        except Exception:
            pass

        return EnvironmentMetadata(
            name="inventory_env",
            description=(
                "Inventory Management — 10 MCP tools for product + order CRUD "
                "over a real SQLite-backed FastAPI. Supports concurrent sessions "
                "with per-session database isolation."
            ),
            version="0.5.0",
            author="RL Gyms Team",
            readme_content=readme_content,
            documentation_url="inventory/README.md",
        )

    def close(self) -> None:
        """
        Clean up resources.

        Deletes the session DB if one was created, then closes the HTTP client.
        """
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
