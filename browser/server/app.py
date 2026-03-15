"""
OpenEnv HTTP/WebSocket Server for the Browser Gym.

Uses OpenEnv's create_app() to auto-generate server routes:
  - POST /reset, POST /step, GET /state, GET /health
  - WebSocket /ws for persistent connections
  - GET /schema, GET /metadata
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

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

try:
    from .browser_environment import BrowserEnvironment
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from browser_environment import BrowserEnvironment


# Discriminated union so both ListToolsAction and CallToolAction deserialise correctly
_mcp_action_adapter = TypeAdapter(Union[ListToolsAction, CallToolAction])


class MCPAction(Action):
    @classmethod
    def model_validate(cls, data: Any, **kwargs: Any) -> Action:
        return _mcp_action_adapter.validate_python(data)


MAX_CONCURRENT_ENVS = int(os.getenv("MAX_CONCURRENT_ENVS", "8"))
OPENENV_PORT = int(os.getenv("OPENENV_PORT", "9003"))

app = create_app(
    BrowserEnvironment,
    MCPAction,
    CallToolObservation,
    env_name="browser_env",
    max_concurrent_envs=MAX_CONCURRENT_ENVS,
)


def main():
    """Start the OpenEnv server. The Express web app must already be running."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=OPENENV_PORT)


if __name__ == "__main__":
    main()
