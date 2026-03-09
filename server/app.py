"""
OpenEnv HTTP Server for the Inventory Environment.

This is the FastAPI application that exposes the OpenEnv interface:
  POST /reset  → Start a new episode
  POST /step   → Agent takes an action
  GET  /state  → Get current episode state
  GET  /health → Health check

How it fits in:
  ┌────────────┐   HTTP    ┌───────────────┐   HTTP    ┌──────────────────┐
  │  AI Agent  │ ────────► │  THIS SERVER  │ ────────► │  Inventory API   │
  │  (Client)  │ ◄──────── │  (port 9000)  │ ◄──────── │  (port 8000)     │
  └────────────┘           └───────────────┘           └──────────────────┘
       Uses                  Translates                  Your existing
    reset/step/state        actions → API calls           FastAPI app

This server runs on port 9000 (separate from your Inventory API on 8000).
"""

import sys
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any

# Add parent directory to path so we can import env_models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inventory_environment import InventoryEnvironment
from env_models import InventoryAction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("openenv.server")

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
INVENTORY_API_URL = os.getenv("INVENTORY_API_URL", "http://localhost:8000")
OPENENV_PORT = int(os.getenv("OPENENV_PORT", "9000"))

# Create the environment instance
env = InventoryEnvironment(api_base_url=INVENTORY_API_URL)


# ──────────────────────────────────────────────
# Request/Response Models for the HTTP endpoints
# ──────────────────────────────────────────────
class ResetRequest(BaseModel):
    """Request body for POST /reset."""
    task_index: int = 0


class StepRequest(BaseModel):
    """Request body for POST /step."""
    tool: str
    parameters: dict[str, Any] = {}


# ──────────────────────────────────────────────
# FastAPI Lifespan (startup/shutdown)
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the environment lifecycle:
    - On startup: Create the HTTP client for talking to the Inventory API
    - On shutdown: Close the HTTP client cleanly
    """
    logger.info(f"🚀 OpenEnv Server starting — connecting to Inventory API at {INVENTORY_API_URL}")
    await env.startup()
    logger.info("✅ Environment ready!")
    yield
    logger.info("🛑 OpenEnv Server shutting down...")
    await env.shutdown()


# ──────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────
app = FastAPI(
    title="Inventory OpenEnv Server",
    description=(
        "OpenEnv-compatible environment for the Inventory Management API.\n\n"
        "## Endpoints\n"
        "- **POST /reset** — Start a new episode\n"
        "- **POST /step** — Agent takes an action\n"
        "- **GET /state** — Get current episode state\n"
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ──────────────────────────────────────────────
# Endpoint: POST /reset
# ──────────────────────────────────────────────
@app.post("/reset")
async def reset(request: ResetRequest = ResetRequest()):
    """
    Start a new episode.

    The agent calls this to begin a fresh training episode.
    It resets the environment state and assigns a task.

    Returns:
        - observation: Initial environment observation (task description)
        - state: Fresh episode state (step_count=0, reward=0)
    """
    logger.info(f"📍 /reset called — task_index={request.task_index}")
    result = await env.reset(request.task_index)
    return result


# ──────────────────────────────────────────────
# Endpoint: POST /step
# ──────────────────────────────────────────────
@app.post("/step")
async def step(request: StepRequest):
    """
    Process one agent action.

    The agent calls this to take an action in the environment.
    The action is translated into an API call to the Inventory system.

    Returns:
        - observation: What happened (success/failure + data)
        - reward: Score for this action (+1 good, -1 bad)
        - done: Is the episode finished?
        - state: Updated episode state
    """
    logger.info(f"📍 /step called — tool={request.tool}, params={request.parameters}")
    action = InventoryAction(tool=request.tool, parameters=request.parameters)
    result = await env.step(action)
    return result


# ──────────────────────────────────────────────
# Endpoint: GET /state
# ──────────────────────────────────────────────
@app.get("/state")
async def state():
    """
    Get the current environment state.

    Returns the current episode's state including:
    - step_count, total_reward, task_description, task_completed, etc.
    """
    result = await env.state()
    return result


# ──────────────────────────────────────────────
# Endpoint: GET /health
# ──────────────────────────────────────────────
@app.get("/health")
async def health():
    """Health check for the OpenEnv server."""
    return {
        "status": "ok",
        "environment": "inventory_env",
        "inventory_api_url": INVENTORY_API_URL,
    }


# ──────────────────────────────────────────────
# Run directly: python server/app.py
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=OPENENV_PORT,
        reload=True,
    )
