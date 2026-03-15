"""
Payment Gateway per-step reward transform.

Extends the base StepRewardTransform with domain-specific scoring based on
the payment lifecycle. Instead of just checking success/failure, it inspects
the API response to score result quality by operation type.

Used when: --reward-mode openenv --gym payment_gateway

Scoring:
    Error (API returned error):                    -0.5
    High-value outcome (succeeded/completed/won):   1.0
    Entity created/retrieved (has id):              0.8
    Negative outcome (failed/lost):                 0.3
    Information query (balance, list):              0.5
    Non-tool observation:                           0.0
"""

import json

from openenv.core.env_server.mcp_types import CallToolObservation
from openenv.core.env_server.types import Observation

from .base import StepRewardTransform

# Statuses that indicate a high-value successful outcome
_SUCCESS_STATUSES = {"succeeded", "completed", "won"}
# Statuses that indicate an expected but negative outcome (not the agent's fault)
_NEGATIVE_STATUSES = {"failed", "lost"}


class PaymentStepTransform(StepRewardTransform):
    """
    Payment Gateway per-step reward.

    Inspects the tool call result and scores based on the payment domain:
      - Successful confirmations, refunds, transfers → 1.0
      - Entity created (customer, payment intent, dispute opened) → 0.8
      - Failed payments, lost disputes → 0.3 (outcome, not agent error)
      - Balance/list queries → 0.5
      - Errors → -0.5
    """

    def _compute_reward(self, observation: Observation) -> float:
        if not isinstance(observation, CallToolObservation):
            return 0.0

        if observation.error is not None:
            return -0.5

        # Extract the actual result data
        result = self._extract_result(observation.result)

        # Dict result — single entity or summary
        if isinstance(result, dict):
            status = result.get("status")

            # Balance endpoint: {"balance": ..., "total_payments": ...}
            if "balance" in result:
                return 0.5

            # Entity with status field (payment, refund, dispute, transfer)
            if status:
                if status in _SUCCESS_STATUSES:
                    return 1.0
                if status in _NEGATIVE_STATUSES:
                    return 0.3
                # Other statuses: "open", "requires_confirmation", etc.
                if "id" in result:
                    return 0.8
                return 0.5

            # Entity without status (customer, session info)
            if "id" in result or "session_id" in result:
                return 0.8

            # List-like wrapper: {"customers": [...], "count": N}
            if "count" in result:
                return 0.5

            return 0.5

        # List result (shouldn't happen in normal MCP flow, but handle it)
        if isinstance(result, list):
            return 0.5 if result else 0.3

        return 0.3

    @staticmethod
    def _extract_result(result):
        """Extract the actual data from the observation result."""
        # Handle MCP CallToolResult wrapper
        if hasattr(result, "data"):
            result = result.data
        elif isinstance(result, dict) and "data" in result:
            result = result["data"]

        # Handle string JSON (from MCP text content)
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                pass

        return result
