"""
OpenEnv type re-exports for the Inventory Environment.

Since this is an MCP-based environment (tools are defined with @mcp.tool),
we use OpenEnv's built-in MCP types — no custom Action/Observation needed.

These re-exports are here for convenience so users can do:
    from models import CallToolAction, CallToolObservation

Instead of the longer:
    from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation
"""

# ── Action types (what the agent sends) ──
from openenv.core.env_server.mcp_types import (
    CallToolAction,       # Call a tool: call_tool("create_product", name="Mouse", ...)
    ListToolsAction,      # Discover tools: list_tools()
)

# ── Observation types (what the agent receives) ──
from openenv.core.env_server.mcp_types import (
    CallToolObservation,  # Result of a tool call (tool_name, result, error)
    ListToolsObservation, # List of available tools (tools=[Tool(...), ...])
)

# ── Base types (for extending if needed later) ──
from openenv.core.env_server.types import (
    Action,       # Base action class
    Observation,  # Base observation class (done, reward, metadata)
    State,        # Base state class (episode_id, step_count)
)

__all__ = [
    "CallToolAction",
    "CallToolObservation",
    "ListToolsAction",
    "ListToolsObservation",
    "Action",
    "Observation",
    "State",
]
