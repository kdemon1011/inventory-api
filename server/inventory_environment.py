"""
OpenEnv Environment Wrapper for the Inventory Management API.

THIS IS THE CORE FILE — it wraps your existing FastAPI inventory API
with the OpenEnv standard interface (reset / step / state).

How it works:
  1. Your original Inventory API runs on port 8000 (unchanged)
  2. This wrapper runs ALONGSIDE it
  3. When the AI agent calls step("create_product", {...}),
     this wrapper translates it into an HTTP POST to /products on your API
  4. It reads the response, computes a REWARD, and sends it all back

Think of this as a TRANSLATOR:
  Agent speaks "OpenEnv language" (reset/step/state)
  Your API speaks "REST language" (GET/POST/PATCH /products /orders)
  This file translates between the two.
"""

import uuid
import logging
import sys
import os

import httpx

# Add parent directory to path so we can import env_models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env_models import InventoryAction, InventoryObservation, InventoryState, AVAILABLE_TOOLS

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# TOOL REGISTRY: Maps tool names → HTTP method + URL path
#
# This is the "translation table":
#   tool name           → HTTP method + API endpoint
#   "create_product"    → POST /products
#   "list_products"     → GET  /products
#   "get_order"         → GET  /orders/{order_id}
#   etc.
# ──────────────────────────────────────────────
TOOL_REGISTRY: dict[str, tuple[str, str]] = {
    "create_product":    ("POST",  "/products"),
    "list_products":     ("GET",   "/products"),
    "search_products":   ("GET",   "/products/search"),
    "get_product":       ("GET",   "/products/{product_id}"),
    "update_product":    ("PATCH", "/products/{product_id}"),
    "create_order":      ("POST",  "/orders"),
    "list_orders":       ("GET",   "/orders"),
    "get_order":         ("GET",   "/orders/{order_id}"),
    "get_order_detail":  ("GET",   "/orders/{order_id}/detail"),
    "get_order_summary": ("GET",   "/orders/{order_id}/summary"),
}


# ──────────────────────────────────────────────
# TASK DEFINITIONS: What the agent is supposed to accomplish
#
# Each task has:
#   - description: Human-readable instruction for the agent
#   - validate: A function that checks if the agent completed the task
#
# The RL training loop will pick a task, give it to the agent,
# and the agent earns rewards for completing it correctly.
# ──────────────────────────────────────────────
TASKS = [
    {
        "id": "task_1",
        "description": (
            "Create a product named 'Wireless Mouse' with SKU 'WM-001', "
            "price 29.99, and stock_quantity 100. "
            "Then verify it exists by listing all products."
        ),
    },
    {
        "id": "task_2",
        "description": (
            "First list all products. Then create an order for customer "
            "'Alice Johnson' (alice@example.com) with 2 units of product_id 1. "
            "Finally, get the order summary."
        ),
    },
    {
        "id": "task_3",
        "description": (
            "Search for products with the word 'Mouse' in their name. "
            "Then update the first matching product to have a new price of 24.99."
        ),
    },
]


class InventoryEnvironment:
    """
    The OpenEnv Environment for Inventory Management.

    This is the main class that an RL training framework interacts with.
    It implements the 3 standard OpenEnv methods:

    1. reset()  → Start a fresh episode, give the agent a task
    2. step()   → Process one agent action, return observation + reward
    3. state()  → Return current episode state

    The reward logic:
      +1.0  → Successful API call
      +2.0  → BONUS for completing the task
      -0.5  → Failed API call (4xx/5xx error)
      -1.0  → Invalid tool name or exception
      -0.1  → Small penalty each step (encourages efficiency)
    """

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize the environment.

        Args:
            api_base_url: URL where your original Inventory API is running.
                          This wrapper will make HTTP calls to this URL.
        """
        self.api_base_url = api_base_url
        self.current_state: InventoryState | None = None
        self.http_client: httpx.AsyncClient | None = None
        self.action_history: list[dict] = []

    async def startup(self):
        """Create the HTTP client. Called when the server starts."""
        self.http_client = httpx.AsyncClient(
            base_url=self.api_base_url,
            timeout=30.0,
        )

    async def shutdown(self):
        """Close the HTTP client. Called when the server stops."""
        if self.http_client:
            await self.http_client.aclose()

    # ──────────────────────────────────────────
    # reset() — Start a fresh episode
    # ──────────────────────────────────────────
    async def reset(self, task_index: int = 0) -> dict:
        """
        Start a brand new episode.

        What happens:
        1. Creates a new unique episode_id
        2. Resets the step counter and reward to 0
        3. Picks a task for the agent to complete
        4. Returns the initial observation (with the task instructions)

        Args:
            task_index: Which task to give the agent (0, 1, or 2)

        Returns:
            dict with "observation" and "state"
        """
        task = TASKS[task_index % len(TASKS)]

        self.current_state = InventoryState(
            episode_id=str(uuid.uuid4()),
            step_count=0,
            total_reward=0.0,
            product_count=0,
            order_count=0,
            task_description=task["description"],
            task_completed=False,
            max_steps=10,
        )

        self.action_history = []

        # Build initial observation — this is what the agent "sees" first
        observation = InventoryObservation(
            success=True,
            data={
                "message": "Environment ready. Complete the following task.",
                "task": task["description"],
                "hint": "Use the available_tools to interact with the Inventory API.",
            },
        )

        logger.info(
            f"Episode {self.current_state.episode_id} started — Task: {task['id']}"
        )

        return {
            "observation": observation.model_dump(),
            "state": self.current_state.model_dump(),
        }

    # ──────────────────────────────────────────
    # step() — Process one agent action
    # ──────────────────────────────────────────
    async def step(self, action: InventoryAction) -> dict:
        """
        Process one action from the agent.

        What happens:
        1. Validate the tool name
        2. Translate the action into an HTTP call to your Inventory API
        3. Get the response
        4. Compute a reward (how well did the agent do?)
        5. Check if the episode is done
        6. Return everything

        Args:
            action: The agent's action (which tool + parameters)

        Returns:
            dict with "observation", "reward", "done", "state"
        """
        if self.current_state is None:
            return {
                "observation": InventoryObservation(
                    success=False,
                    error="Environment not initialized. Call reset() first.",
                ).model_dump(),
                "reward": -1.0,
                "done": True,
                "state": None,
            }

        self.current_state.step_count += 1

        # Record what the agent did (for debugging/analysis)
        self.action_history.append({
            "step": self.current_state.step_count,
            "tool": action.tool,
            "parameters": action.parameters,
        })

        # ── CHECK 1: Is the tool valid? ──
        if action.tool not in TOOL_REGISTRY:
            observation = InventoryObservation(
                success=False,
                error=(
                    f"Unknown tool: '{action.tool}'. "
                    f"Available tools: {AVAILABLE_TOOLS}"
                ),
            )
            reward = -1.0  # Harsh penalty for using a tool that doesn't exist
            done = self.current_state.step_count >= self.current_state.max_steps
            self.current_state.total_reward += reward
            logger.warning(f"Step {self.current_state.step_count}: Invalid tool '{action.tool}'")
            return {
                "observation": observation.model_dump(),
                "reward": reward,
                "done": done,
                "state": self.current_state.model_dump(),
            }

        # ── EXECUTE: Call your Inventory API ──
        method, path_template = TOOL_REGISTRY[action.tool]

        try:
            # Build the URL path (replace {product_id}, {order_id}, etc.)
            path = path_template
            params = dict(action.parameters)  # copy so we don't mutate

            # Extract path parameters (e.g., product_id=1 → /products/1)
            for key in list(params.keys()):
                placeholder = f"{{{key}}}"
                if placeholder in path:
                    path = path.replace(placeholder, str(params.pop(key)))

            # Make the HTTP call to your existing Inventory API
            if method == "GET":
                response = await self.http_client.get(path, params=params)
            elif method == "POST":
                response = await self.http_client.post(path, json=params)
            elif method == "PATCH":
                response = await self.http_client.patch(path, json=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # ── BUILD OBSERVATION from API response ──
            if response.status_code < 400:
                data = response.json()
                observation = InventoryObservation(success=True, data=data)
                reward = 1.0  # Successful API call = positive reward

                logger.info(
                    f"Step {self.current_state.step_count}: "
                    f"{action.tool} → SUCCESS (HTTP {response.status_code})"
                )
            else:
                error_text = response.text[:200]  # Truncate long errors
                observation = InventoryObservation(
                    success=False,
                    error=f"API returned HTTP {response.status_code}: {error_text}",
                )
                reward = -0.5  # Penalty for bad API call

                logger.warning(
                    f"Step {self.current_state.step_count}: "
                    f"{action.tool} → FAILED (HTTP {response.status_code})"
                )

        except Exception as exc:
            observation = InventoryObservation(
                success=False,
                error=f"Exception: {str(exc)}",
            )
            reward = -1.0  # Harsh penalty for crashing
            logger.error(f"Step {self.current_state.step_count}: Exception — {exc}")

        # ── STEP PENALTY: Small cost per step to encourage efficiency ──
        reward -= 0.1

        # ── CHECK: Is the episode done? ──
        done = self.current_state.step_count >= self.current_state.max_steps

        # Update state
        self.current_state.total_reward += reward

        return {
            "observation": observation.model_dump(),
            "reward": round(reward, 2),
            "done": done,
            "state": self.current_state.model_dump(),
        }

    # ──────────────────────────────────────────
    # state() — Get current episode state
    # ──────────────────────────────────────────
    async def state(self) -> dict:
        """
        Return the current state of the episode.

        This lets the agent (or monitoring tools) check:
        - How many steps have been taken
        - What the total reward is
        - Whether the task is complete
        """
        if self.current_state is None:
            return {"state": None, "message": "No active episode. Call reset() first."}
        return {
            "state": self.current_state.model_dump(),
            "action_history": self.action_history,
        }
