"""
Browser Gym — MCPEnvironment that exposes browser-like MCP tools.

The agent navigates pages, clicks elements, fills forms, and asserts DOM state
through these tools. Internally, each tool calls the Express API via HTTP.

Tools are registered in __init__ and defined in Step 3 (web app integration).
This file is a scaffold — tool implementations are added after the web app is built.
"""

import os
import uuid

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from openenv.core.env_server.mcp_env import MCPEnvironment
from openenv.core.env_server.mcp_types import EnvironmentMetadata

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8003")


class BrowserEnvironment(MCPEnvironment):
    """
    OpenEnv environment for browser-like interaction with a web application.

    The agent uses MCP tools (navigate, click, fill_form, etc.) to interact
    with an e-commerce web app. All state is managed per-session via X-Session-ID.
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        mcp = FastMCP("browser_gym")
        self._session_id = None
        self._current_page = "/"
        self._auth_token = None
        self._form_data = {}
        self._webapp_url = WEBAPP_URL

        # ── Infrastructure tool ──

        @mcp.tool()
        def get_session_info() -> dict:
            """Returns the current session ID for this environment instance."""
            return {"session_id": self._session_id or "none"}

        # ── Browser-like tools (implementations added in Step 3) ──
        # Placeholder — navigate, get_page_content, click_element, fill_form,
        # submit_form, search_products, get_element_text, add_to_cart,
        # update_cart_item, remove_from_cart, get_cart, checkout,
        # toggle_wishlist, assert_text_visible

        super().__init__(mcp)

    def _headers(self) -> dict:
        """Build request headers with session and auth context."""
        h = {}
        if self._session_id:
            h["X-Session-ID"] = self._session_id
        if self._auth_token:
            h["Authorization"] = f"Bearer {self._auth_token}"
        return h

    async def reset(self):
        """Reset environment: create a new session, clear browser state."""
        self._session_id = str(uuid.uuid4())
        self._current_page = "/"
        self._auth_token = None
        self._form_data = {}

        # Create isolated session DB via the Express API
        async with httpx.AsyncClient(base_url=self._webapp_url, timeout=10.0) as client:
            await client.post("/api/sessions", json={"session_id": self._session_id})

        return await super().reset()

    async def close(self):
        """Cleanup: delete the session DB."""
        if self._session_id:
            try:
                async with httpx.AsyncClient(base_url=self._webapp_url, timeout=10.0) as client:
                    await client.delete(f"/api/sessions/{self._session_id}")
            except Exception:
                pass
        return await super().close()

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
            doc_url="https://github.com/kdemon1011/inventory-api/blob/main/browser/README.md",
        )
