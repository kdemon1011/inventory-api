"""
Inventory-specific per-step reward transform.

Extends the base StepRewardTransform with inventory result validation.
Instead of just checking success/failure, it also inspects the API response
structure to score result quality.

Used when: --reward-mode openenv --gym inventory
"""

from openenv.core.env_server.mcp_types import CallToolObservation
from openenv.core.env_server.types import Observation

from .base import StepRewardTransform


class InventoryStepTransform(StepRewardTransform):
    """
    Inventory-specific per-step reward.

    Scoring:
        Error (API returned error):              -0.5
        Created/retrieved entity (dict with id):   1.0
        Listed entities (non-empty list):          0.8
        Valid but empty/minimal result:            0.5
        Non-tool observation:                      0.0
    """

    def _compute_reward(self, observation: Observation) -> float:
        if not isinstance(observation, CallToolObservation):
            return 0.0

        if observation.error is not None:
            return -0.5

        # Extract the actual result data
        result = observation.result
        if hasattr(result, "data"):
            result = result.data
        elif isinstance(result, dict) and "data" in result:
            result = result["data"]

        # Score based on result structure
        if isinstance(result, dict):
            # Single entity (create/get/update) — high confidence if 'id' present
            if "id" in result:
                return 1.0
            return 0.5

        if isinstance(result, list):
            # List operation — good if non-empty
            if len(result) > 0:
                return 0.8
            return 0.5

        # Some result but unclear structure
        return 0.5
