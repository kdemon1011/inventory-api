"""
Payment Gateway Environment Client — extends OpenEnv's MCPToolClient.

Provides the client class and type aliases required for
OpenEnv's AutoEnv / AutoAction auto-discovery system.

AutoEnv discovery expects three exports in <module>.client:
    - PaymentGatewayEnv         (client)       — the EnvClient subclass
    - PaymentGatewayAction      (action)       — the Action type
    - PaymentGatewayObservation  (observation) — the Observation type

Usage (manual):
    >>> from payment_gateway.client import PaymentGatewayEnv
    >>> with PaymentGatewayEnv(base_url="http://localhost:9002") as env:
    ...     env.reset()
    ...     tools = env.list_tools()
    ...     result = env.call_tool("create_payment", amount=5000, currency="usd", customer_email="alice@test.com")

Usage (auto-discovery):
    >>> from openenv import AutoEnv
    >>> env = AutoEnv.from_env("payment_gateway", base_url="http://localhost:9002")
"""

from openenv.core.mcp_client import MCPToolClient
from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation


class PaymentGatewayEnv(MCPToolClient):
    """
    Client for the Payment Gateway OpenEnv Environment.

    Inherits from MCPToolClient which provides:
      list_tools(), call_tool(), reset(), step(), state()

    Discoverable via: AutoEnv.from_env("payment_gateway")
    """

    pass


# ── Type aliases for AutoEnv / AutoAction discovery ──
PaymentGatewayAction = CallToolAction
PaymentGatewayObservation = CallToolObservation
