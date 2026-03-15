"""
Browser Gym — per-step reward transform.

Extends StepRewardTransform with browser-specific scoring based on
which tool was called and the quality of the result.

Scoring rationale:
  - Browser tools fall into 4 tiers by action significance:
    1. Major mutations (checkout, submit_form, review) → high reward for success
    2. Cart/wishlist modifications → medium-high reward
    3. Navigation and search → medium reward (necessary but not goal-achieving)
    4. Reading/infrastructure (get_page_content, fill_form) → low reward
  - Errors always penalize (-0.5) regardless of tool
  - Assertions that pass get higher reward than assertions that fail

Used when: --reward-mode openenv --gym browser
"""

from openenv.core.env_server.mcp_types import CallToolObservation
from openenv.core.env_server.types import Observation

from .base import StepRewardTransform


# Tools grouped by action significance
_MUTATION_TOOLS = {"checkout", "submit_form"}
_CART_TOOLS = {"add_to_cart", "update_cart_item", "remove_from_cart", "toggle_wishlist"}
_NAVIGATION_TOOLS = {"navigate", "search_products", "click_element"}
_READ_TOOLS = {"get_page_content", "get_element_text", "get_cart", "get_session_info", "fill_form"}
_ASSERT_TOOLS = {"assert_text_visible"}


class BrowserStepTransform(StepRewardTransform):
    """
    Browser-specific per-step reward.

    Scoring:
        Error (any tool):                          -0.5
        checkout / submit_form success:             1.0
        add_to_cart / update / remove / wishlist:   0.8
        navigate / search / click success:          0.5
        assert_text_visible (visible=true):         0.8
        assert_text_visible (visible=false):        0.3
        get_cart / get_page_content / fill_form:    0.3
        get_session_info:                           0.1
        Unknown tool success:                       0.5
    """

    def _compute_reward(self, observation: Observation) -> float:
        if not isinstance(observation, CallToolObservation):
            return 0.0

        if observation.error is not None:
            return -0.5

        tool = observation.tool_name
        result = observation.result

        # Unwrap result if nested
        if hasattr(result, "data"):
            result = result.data
        elif isinstance(result, dict) and "data" in result:
            result = result["data"]

        # Check for tool-level errors in the result
        if isinstance(result, dict) and "error" in result:
            return -0.5

        # Major mutations: checkout, form submissions
        if tool in _MUTATION_TOOLS:
            if isinstance(result, dict):
                # Checkout success has order_id; form submissions have various success indicators
                if any(k in result for k in ("order_id", "token", "id", "submitted", "updated", "moved")):
                    return 1.0
                # Successful but minimal response
                return 0.8
            return 0.5

        # Cart/wishlist modifications
        if tool in _CART_TOOLS:
            if isinstance(result, dict):
                if "error" not in result:
                    return 0.8
            return 0.5

        # Navigation/search/click
        if tool in _NAVIGATION_TOOLS:
            if isinstance(result, dict):
                # Navigation returns page content with elements
                if "elements" in result or "products" in result:
                    return 0.5
                # Click returned meaningful result
                if any(k in result for k in ("order_id", "moved", "deleted", "id")):
                    return 0.8
                return 0.4
            return 0.3

        # Assertion tool
        if tool in _ASSERT_TOOLS:
            if isinstance(result, dict):
                if result.get("visible") is True:
                    return 0.8
                return 0.3
            return 0.3

        # Read/infrastructure tools
        if tool in _READ_TOOLS:
            if tool == "get_session_info":
                return 0.1
            if tool == "fill_form":
                return 0.2
            # get_cart, get_page_content, get_element_text
            if isinstance(result, dict):
                return 0.3
            return 0.2

        # Unknown tool — default
        return 0.5
