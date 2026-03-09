"""
Inventory Environment Client — extends OpenEnv's MCPToolClient.

This client connects to the Inventory OpenEnv server and provides:
  - list_tools()          → Discover all 10 inventory tools
  - call_tool(name, ...)  → Call a tool (e.g., create_product, create_order)
  - reset()               → Reset the environment for a new episode
  - step(action)          → Execute a raw action (advanced usage)
  - state()               → Get current episode state

The client uses WebSocket for persistent, low-latency communication.
For sync usage (scripts, testing), use .sync() to get a SyncEnvClient.

Example (sync — for testing):
    >>> from client import InventoryEnv
    >>>
    >>> with InventoryEnv(base_url="http://localhost:9000").sync() as env:
    ...     env.reset()
    ...
    ...     # Discover tools
    ...     tools = env.list_tools()
    ...     for t in tools:
    ...         print(f"  {t.name}: {t.description}")
    ...
    ...     # Use tools
    ...     result = env.call_tool("create_product",
    ...         name="Mouse", sku="M1", price=9.99)
    ...     print(result)

Example (async — for RL training):
    >>> import asyncio
    >>> from client import InventoryEnv
    >>>
    >>> async def main():
    ...     async with InventoryEnv(base_url="http://localhost:9000") as env:
    ...         await env.reset()
    ...         tools = await env.list_tools()
    ...         result = await env.call_tool("create_product",
    ...             name="Keyboard", sku="K1", price=49.99)
    ...
    >>> asyncio.run(main())

Example (from Docker):
    >>> env = InventoryEnv.from_docker_image("inventory-env:latest")

Example (from HuggingFace):
    >>> env = InventoryEnv.from_env("your-org/inventory-env")
"""

from openenv.core.mcp_client import MCPToolClient


class InventoryEnv(MCPToolClient):
    """
    Client for the Inventory OpenEnv Environment.

    Inherits ALL functionality from MCPToolClient:
      - list_tools()           → discover available tools
      - call_tool(name, ...)   → call a tool by name
      - reset(**kwargs)        → reset the environment
      - step(action)           → execute an action
      - state()                → get current state
      - .sync()                → get synchronous wrapper

    This class is intentionally minimal — MCPToolClient provides everything.
    You only need to add custom methods if your environment needs special client logic.
    """

    pass  # MCPToolClient provides all needed functionality
