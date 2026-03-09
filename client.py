"""
Inventory Environment Client — extends OpenEnv's MCPToolClient.

Usage:
    >>> from client import InventoryEnv
    >>>
    >>> with InventoryEnv(base_url="http://localhost:9000") as env:
    ...     env.reset()
    ...     tools = env.list_tools()
    ...     result = env.call_tool("list_products", active_only=True)
"""

from openenv.core.mcp_client import MCPToolClient


class InventoryEnv(MCPToolClient):
    """
    Client for the Inventory OpenEnv Environment.

    Inherits from MCPToolClient which provides:
      list_tools(), call_tool(), reset(), step(), state()
    """

    pass
