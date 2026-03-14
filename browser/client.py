"""
Browser Gym Client — extends OpenEnv's MCPToolClient.

AutoEnv discovery expects three exports:
    - BrowserEnv          (client)      — the EnvClient subclass
    - BrowserAction       (action)      — the Action type
    - BrowserObservation  (observation) — the Observation type

Usage (manual):
    >>> from browser_gym.client import BrowserEnv
    >>> with BrowserEnv(base_url="http://localhost:9003") as env:
    ...     env.reset()
    ...     tools = env.list_tools()
    ...     result = env.call_tool("navigate", route="/products")

Usage (auto-discovery):
    >>> from openenv import AutoEnv
    >>> env = AutoEnv.from_env("browser_gym", base_url="http://localhost:9003")
"""

from openenv.core.mcp_client import MCPToolClient
from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation


class BrowserEnv(MCPToolClient):
    """Client for the Browser Gym OpenEnv Environment."""
    pass


BrowserAction = CallToolAction
BrowserObservation = CallToolObservation
