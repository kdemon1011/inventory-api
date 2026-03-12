"""
Inventory Environment Client — extends OpenEnv's MCPToolClient.

This module provides the client class and type aliases required for
OpenEnv's AutoEnv / AutoAction auto-discovery system.

AutoEnv discovery expects three classes in <module>.client:
    - InventoryEnv          (client)       — the EnvClient subclass
    - InventoryAction       (action)       — the Action type
    - InventoryObservation  (observation)  — the Observation type

Since the inventory gym uses MCP tools (not typed actions), the action
and observation types are the standard MCP ones aliased here.

Usage (manual):
    >>> from inventory.client import InventoryEnv
    >>> with InventoryEnv(base_url="http://localhost:9000") as env:
    ...     env.reset()
    ...     tools = env.list_tools()
    ...     result = env.call_tool("list_products", active_only=True)

Usage (auto-discovery):
    >>> from openenv import AutoEnv
    >>> env = AutoEnv.from_env("inventory", base_url="http://localhost:9000")
    >>> env.reset()
    >>> tools = env.list_tools()
"""

from openenv.core.mcp_client import MCPToolClient
from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation


class InventoryEnv(MCPToolClient):
    """
    Client for the Inventory OpenEnv Environment.

    Inherits from MCPToolClient which provides:
      list_tools(), call_tool(), reset(), step(), state()

    Discoverable via: AutoEnv.from_env("inventory")
    """

    pass


# ── Type aliases for AutoEnv / AutoAction discovery ──
# AutoAction.from_env("inventory") returns InventoryAction
# These are standard MCP types since this gym uses tool-based interaction.
InventoryAction = CallToolAction
InventoryObservation = CallToolObservation
