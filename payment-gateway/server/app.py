"""
OpenEnv HTTP/WebSocket Server for the Payment Gateway Environment.

Uses OpenEnv's create_app() to auto-generate all server routes:
  - POST /reset, POST /step, GET /state, GET /health
  - WebSocket /ws for persistent connections
  - GET /schema, GET /metadata, GET / (Web UI)

Concurrent Sessions:
  MAX_CONCURRENT_ENVS controls simultaneous WebSocket sessions (default: 4).
  Each session gets its own PaymentEnvironment instance with an isolated DB.
"""

import os
import sys
from pathlib import Path
from typing import Any, Union

from pydantic import TypeAdapter

from openenv.core.env_server.http_server import create_app
from openenv.core.env_server.mcp_types import (
    CallToolAction,
    CallToolObservation,
    ListToolsAction,
)
from openenv.core.env_server.types import Action

# Support running as package or standalone
try:
    from .payment_environment import PaymentEnvironment
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from payment_environment import PaymentEnvironment


# ── Discriminated Union for MCP Actions ──
_mcp_action_adapter = TypeAdapter(Union[ListToolsAction, CallToolAction])


class MCPAction(Action):
    """Discriminated-union action that deserialises to the correct MCP action."""

    @classmethod
    def model_validate(cls, data: Any, **kwargs: Any) -> Action:
        return _mcp_action_adapter.validate_python(data)


# ── Config ──
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

MAX_CONCURRENT_ENVS = int(os.getenv("MAX_CONCURRENT_ENVS", "4"))
OPENENV_PORT = int(os.getenv("OPENENV_PORT", "9002"))

# ── Create the OpenEnv app ──
app = create_app(
    PaymentEnvironment,
    MCPAction,
    CallToolObservation,
    env_name="payment_gateway",
    max_concurrent_envs=MAX_CONCURRENT_ENVS,
)


def main():
    """Entry point — starts the OpenEnv server on OPENENV_PORT (default 9002)."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=OPENENV_PORT)


if __name__ == "__main__":
    main()
