"""
Browser Gym — MCPEnvironment with 15 browser-like MCP tools.

The agent navigates pages, clicks elements, fills forms, and asserts DOM state.
Internally, each tool calls the Express API (port 8003) via HTTP.
Session isolation via X-Session-ID header on all requests.
"""

import os
import re
import uuid
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from openenv.core.env_server.mcp_environment import MCPEnvironment
from openenv.core.env_server.types import Action, EnvironmentMetadata, Observation, State

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8003")


class BrowserEnvironment(MCPEnvironment):
    """
    OpenEnv environment for browser-like interaction with a web application.

    15 MCP tools simulate browser actions: navigate, click, fill forms, search,
    manage cart/wishlist, checkout, and assert page content. All state is
    per-session via X-Session-ID headers forwarded to the Express API.
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        mcp = FastMCP("browser_gym")
        self._session_id = None
        self._current_route = "/"
        self._page_content = {}
        self._auth_token = None
        self._form_data = {}
        self._http = httpx.Client(base_url=WEBAPP_URL, timeout=30.0)
        self._state = State(episode_id="", step_count=0)

        # ── Tool 1: Infrastructure ──

        @mcp.tool()
        def get_session_info() -> dict:
            """Returns the current session ID for this environment instance."""
            return {"session_id": self._session_id or "none"}

        # ── Tool 2: Navigate ──

        @mcp.tool()
        def navigate(route: str) -> dict:
            """Navigate to a page by route (e.g. '/products', '/login', '/cart').
            Returns the page content as structured JSON with all visible elements."""
            self._current_route = route
            self._form_data = {}
            result = self._api("GET", f"/api/page{route}")
            if "error" not in result:
                self._page_content = result
            return result

        # ── Tool 3: Get Page Content ──

        @mcp.tool()
        def get_page_content() -> dict:
            """Get the current page's content (from last navigation). No re-fetch."""
            if not self._page_content:
                return {"error": "No page loaded. Use navigate() first."}
            return self._page_content

        # ── Tool 4: Click Element ──

        @mcp.tool()
        def click_element(element_id: str) -> dict:
            """Click an element on the current page by its ID.
            Handles buttons (add-to-cart, remove, cancel, etc.) and links (navigation)."""

            # Add to cart: add-to-cart-{product_id}
            m = re.match(r"add-to-cart-(\d+)$", element_id)
            if m:
                return self._api("POST", "/api/cart", {"product_id": int(m.group(1)), "quantity": 1})

            # Add to wishlist: add-to-wishlist-{product_id}
            m = re.match(r"add-to-wishlist-(\d+)$", element_id)
            if m:
                return self._api("POST", "/api/wishlist", {"product_id": int(m.group(1))})

            # Remove wishlist item: remove-wishlist-{wishlist_item_id}
            m = re.match(r"remove-wishlist-(\d+)$", element_id)
            if m:
                return self._api("DELETE", f"/api/wishlist/{m.group(1)}")

            # Move wishlist to cart: move-to-cart-{wishlist_item_id}
            m = re.match(r"move-to-cart-(\d+)$", element_id)
            if m:
                return self._api("POST", f"/api/wishlist/{m.group(1)}/move-to-cart")

            # Remove cart item: remove-{cart_item_id}
            m = re.match(r"remove-(\d+)$", element_id)
            if m:
                return self._api("DELETE", f"/api/cart/{m.group(1)}")

            # Clear entire cart
            if element_id == "clear-cart":
                return self._api("DELETE", "/api/cart")

            # Cancel order (order_id from current page content)
            if element_id == "cancel-order":
                order_id = self._page_content.get("elements", {}).get("order", {}).get("id")
                if not order_id:
                    return {"error": "No order found on current page"}
                return self._api("PUT", f"/api/orders/{order_id}/cancel")

            # Checkout button → navigate to /checkout
            if element_id == "checkout-btn":
                return navigate("/checkout")

            # Apply coupon (reads coupon_code from form_data)
            if element_id == "apply-coupon":
                code = self._form_data.get("coupon_code", "")
                if not code:
                    return {"error": "No coupon code entered. Use fill_form('coupon_code', 'CODE') first."}
                return self._api("POST", "/api/coupons/validate", {"code": code})

            # Place order → submit the shipping form
            if element_id == "place-order":
                return submit_form("shipping-form")

            # Form submit buttons → delegate to submit_form
            form_buttons = {
                "login-submit": "login-form",
                "register-submit": "register-form",
                "send-message": "contact-form",
                "submit-review": "review-form",
                "update-profile": "profile-form",
                "change-password": "password-form",
            }
            if element_id in form_buttons:
                return submit_form(form_buttons[element_id])

            # Try to find element with href → navigate
            elem = self._find_element(element_id)
            if elem and "href" in elem:
                return navigate(elem["href"])
            if elem:
                return {"element": elem, "note": "Element found but has no clickable action"}

            return {"error": f"Element '{element_id}' not found on page '{self._current_route}'"}

        # ── Tool 5: Fill Form ──

        @mcp.tool()
        def fill_form(field_name: str, value: str) -> dict:
            """Fill a form field by name. Call submit_form() after filling all fields."""
            self._form_data[field_name] = value
            return {
                "status": "ok",
                "field": field_name,
                "page": self._current_route,
                "filled_fields": list(self._form_data.keys()),
            }

        # ── Tool 6: Submit Form ──

        @mcp.tool()
        def submit_form(form_id: str) -> dict:
            """Submit a form using fields set via fill_form(). Clears form data after submission.

            Known forms: login-form, register-form, contact-form, review-form,
            profile-form, password-form, shipping-form."""
            data = dict(self._form_data)
            self._form_data = {}

            if form_id == "login-form":
                result = self._api("POST", "/api/auth/login", data)
                if "token" in result:
                    self._auth_token = result["token"]
                return result

            if form_id == "register-form":
                result = self._api("POST", "/api/auth/register", data)
                if "token" in result:
                    self._auth_token = result["token"]
                return result

            if form_id == "contact-form":
                return self._api("POST", "/api/contact", data)

            if form_id == "review-form":
                pid = self._page_content.get("elements", {}).get("product", {}).get("id")
                if not pid:
                    return {"error": "Not on a product detail page. Navigate to /products/{id} first."}
                if "rating" in data:
                    try:
                        data["rating"] = int(data["rating"])
                    except ValueError:
                        return {"error": "Rating must be a number between 1 and 5"}
                return self._api("POST", f"/api/products/{pid}/reviews", data)

            if form_id == "profile-form":
                return self._api("PUT", "/api/profile", data)

            if form_id == "password-form":
                return self._api("PUT", "/api/profile/password", data)

            if form_id == "shipping-form":
                return self._api("POST", "/api/orders/checkout", data)

            return {"error": f"Unknown form: {form_id}"}

        # ── Tool 7: Search Products ──

        @mcp.tool()
        def search_products(query: str = "", category: str = "", sort: str = "") -> dict:
            """Search products. Optional: query (text), category (Electronics/Clothing/Books/Home),
            sort (price_asc/price_desc)."""
            params = {}
            if query:
                params["q"] = query
            if category:
                params["category"] = category
            if sort:
                params["sort"] = sort
            return self._api("GET", "/api/products", params=params)

        # ── Tool 8: Get Element Text ──

        @mcp.tool()
        def get_element_text(element_id: str) -> dict:
            """Get the content/properties of a specific element by its ID on the current page."""
            elem = self._find_element(element_id)
            if elem:
                return {"element_id": element_id, "content": elem}
            return {"error": f"Element '{element_id}' not found on page '{self._current_route}'"}

        # ── Tool 9: Add to Cart ──

        @mcp.tool()
        def add_to_cart(product_id: int, quantity: int = 1) -> dict:
            """Add a product to the cart by product ID and quantity."""
            return self._api("POST", "/api/cart", {"product_id": product_id, "quantity": quantity})

        # ── Tool 10: Update Cart Item ──

        @mcp.tool()
        def update_cart_item(cart_item_id: int, quantity: int) -> dict:
            """Update the quantity of a cart item."""
            return self._api("PUT", f"/api/cart/{cart_item_id}", {"quantity": quantity})

        # ── Tool 11: Remove from Cart ──

        @mcp.tool()
        def remove_from_cart(cart_item_id: int) -> dict:
            """Remove an item from the cart by cart item ID."""
            return self._api("DELETE", f"/api/cart/{cart_item_id}")

        # ── Tool 12: Get Cart ──

        @mcp.tool()
        def get_cart() -> dict:
            """Get current cart contents with item details, quantities, subtotals, and grand total."""
            return self._api("GET", "/api/cart")

        # ── Tool 13: Checkout ──

        @mcp.tool()
        def checkout(shipping_name: str, shipping_address: str, shipping_city: str,
                     shipping_zip: str, coupon_code: str = "") -> dict:
            """Complete checkout with shipping details and optional coupon code.
            Cart must have items. Returns order details including total and discount."""
            data = {
                "shipping_name": shipping_name,
                "shipping_address": shipping_address,
                "shipping_city": shipping_city,
                "shipping_zip": shipping_zip,
            }
            if coupon_code:
                data["coupon_code"] = coupon_code
            return self._api("POST", "/api/orders/checkout", data)

        # ── Tool 14: Toggle Wishlist ──

        @mcp.tool()
        def toggle_wishlist(product_id: int) -> dict:
            """Add a product to the wishlist. If already in wishlist, removes it instead."""
            result = self._api("POST", "/api/wishlist", {"product_id": product_id})
            if "error" in result and "already in wishlist" in result.get("error", "").lower():
                wishlist = self._api("GET", "/api/wishlist")
                for item in wishlist.get("items", []):
                    if item.get("product_id") == product_id:
                        return self._api("DELETE", f"/api/wishlist/{item['id']}")
                return {"error": "Product reported in wishlist but item not found"}
            return result

        # ── Tool 15: Assert Text Visible ──

        @mcp.tool()
        def assert_text_visible(text: str) -> dict:
            """Check if specific text is visible anywhere on the current page.
            Returns {visible: true/false, text, page}."""
            found = self._search_text(self._page_content, text)
            return {"visible": found, "text": text, "page": self._current_route}

        super().__init__(mcp)

    # ── Internal helpers (not exposed as tools) ──

    def _headers(self) -> dict:
        """Build request headers with session and auth context."""
        h = {}
        if self._session_id:
            h["X-Session-ID"] = self._session_id
        if self._auth_token:
            h["Authorization"] = f"Bearer {self._auth_token}"
        return h

    def _api(self, method: str, path: str, json_data: dict = None, params: dict = None) -> dict:
        """Make an HTTP request to the Express API. Returns parsed JSON."""
        try:
            resp = self._http.request(method, path, headers=self._headers(),
                                      json=json_data, params=params)
            try:
                return resp.json()
            except Exception:
                return {"error": resp.text[:500], "status_code": resp.status_code}
        except Exception as e:
            return {"error": str(e)}

    def _find_element(self, element_id: str):
        """Recursively search page content for an element with matching 'id' field."""
        def search(obj):
            if isinstance(obj, dict):
                if obj.get("id") == element_id:
                    return obj
                for v in obj.values():
                    r = search(v)
                    if r:
                        return r
            elif isinstance(obj, list):
                for item in obj:
                    r = search(item)
                    if r:
                        return r
            return None
        return search(self._page_content)

    @staticmethod
    def _search_text(obj, text: str) -> bool:
        """Recursively check if text appears anywhere in a nested structure."""
        target = text.lower()
        if isinstance(obj, str):
            return target in obj.lower()
        if isinstance(obj, (int, float)):
            return target in str(obj).lower()
        if isinstance(obj, dict):
            return any(BrowserEnvironment._search_text(v, text) for v in obj.values())
        if isinstance(obj, list):
            return any(BrowserEnvironment._search_text(item, text) for item in obj)
        return False

    # ── Gymnasium-style lifecycle ──

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Observation:
        """Reset: create a new session, clear all browser state."""
        self._session_id = str(uuid.uuid4())
        self._current_route = "/"
        self._page_content = {}
        self._auth_token = None
        self._form_data = {}

        # Create isolated session DB via Express API
        try:
            resp = self._http.post(
                "/api/sessions",
                json={"session_id": self._session_id},
            )
            resp.raise_for_status()
        except Exception:
            self._session_id = None

        self._state = State(
            episode_id=episode_id or self._session_id or str(uuid.uuid4()),
            step_count=0,
        )

        return Observation(
            done=False,
            reward=0.0,
            metadata={"status": "ready", "session_id": self._session_id},
        )

    def _step_impl(
        self,
        action: Action,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """Handle non-MCP actions (fallback). All real work goes through MCP tools."""
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
        """Execute a step. Tracks step count then delegates to MCPEnvironment."""
        self._state.step_count += 1
        return super().step(action, timeout_s=timeout_s, **kwargs)

    @property
    def state(self) -> State:
        """Get the current environment state."""
        return self._state

    def close(self) -> None:
        """Cleanup: delete session DB, close HTTP client."""
        if self._session_id:
            try:
                self._http.delete(f"/api/sessions/{self._session_id}")
            except Exception:
                pass
        self._http.close()
        super().close()

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="browser_gym",
            version="0.1.0",
            description=(
                "Browser Gym — navigate, interact with, and assert on a full-stack "
                "e-commerce web application through 15 browser-like MCP tools. "
                "Built on Node.js/Express + React, with SQLite for persistence."
            ),
            author="OpenEnv Team",
            documentation_url="https://github.com/kdemon1011/inventory-api/blob/main/browser/README.md",
        )
