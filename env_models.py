"""
OpenEnv Data Models for the Inventory Environment.

These models define the LANGUAGE of your environment:
- InventoryAction:      What the AI agent CAN DO (which API tool + parameters)
- InventoryObservation: What the agent SEES after acting (success, data, errors)  
- InventoryState:       The episode's current STATUS (step count, reward, etc.)

Think of it like this:
  Action      = the agent's "mouth" (it says what it wants to do)
  Observation = the agent's "eyes" (it sees what happened)
  State       = the agent's "memory" (it knows where it is in the episode)
"""

from pydantic import BaseModel, Field
from typing import Optional, Any


# ──────────────────────────────────────────────
# All available tools (API endpoints) the agent can call
# ──────────────────────────────────────────────
AVAILABLE_TOOLS = [
    "create_product",
    "list_products",
    "search_products",
    "get_product",
    "update_product",
    "create_order",
    "list_orders",
    "get_order",
    "get_order_detail",
    "get_order_summary",
]


class InventoryAction(BaseModel):
    """
    What the AI agent wants to DO.

    Example:
        InventoryAction(
            tool="create_product",
            parameters={"name": "Mouse", "sku": "M-001", "price": 29.99}
        )

    The agent picks:
      - tool: WHICH API endpoint to call (from the AVAILABLE_TOOLS list)
      - parameters: WHAT data to send (depends on the tool)
    """

    tool: str = Field(
        ...,
        description="Which API tool to use. Must be one of the available tools.",
        examples=["create_product", "list_products", "create_order"],
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to pass to the selected tool.",
    )


class InventoryObservation(BaseModel):
    """
    What the AI agent SEES after taking an action.

    This is the environment's "response" to the agent:
      - success: Did the action work? (True/False)
      - data: The actual response data from the API (if successful)
      - error: Error message (if something went wrong)
      - available_tools: Reminder of what tools the agent can use

    Example (successful):
        InventoryObservation(
            success=True,
            data={"id": 1, "name": "Mouse", "sku": "M-001", "price": 29.99, ...}
        )

    Example (failed):
        InventoryObservation(
            success=False,
            error="product 99 not found"
        )
    """

    success: bool = Field(description="Did the action succeed?")
    data: Any = Field(default=None, description="Response data from the API call")
    error: Optional[str] = Field(
        default=None, description="Error message if the action failed"
    )
    available_tools: list[str] = Field(
        default_factory=lambda: AVAILABLE_TOOLS.copy(),
        description="List of tools the agent can use in this environment",
    )


class InventoryState(BaseModel):
    """
    The current state of the environment episode.

    Tracks what's happened so far in this episode:
      - episode_id: Unique ID for this episode (like a session ID)
      - step_count: How many actions the agent has taken so far
      - total_reward: Cumulative reward the agent has earned
      - product_count: How many products exist in the database
      - order_count: How many orders exist in the database
      - task_description: What the agent is supposed to accomplish
      - task_completed: Has the agent finished the task?
      - max_steps: Maximum steps allowed before the episode ends

    This is like the "scoreboard" of the current game.
    """

    episode_id: str = Field(description="Unique identifier for this episode")
    step_count: int = Field(default=0, description="Number of actions taken so far")
    total_reward: float = Field(default=0.0, description="Cumulative reward earned")
    product_count: int = Field(default=0, description="Number of products in the DB")
    order_count: int = Field(default=0, description="Number of orders in the DB")
    task_description: str = Field(
        default="", description="What the agent should accomplish"
    )
    task_completed: bool = Field(
        default=False, description="Whether the task has been completed"
    )
    max_steps: int = Field(
        default=10, description="Maximum steps before the episode ends"
    )
