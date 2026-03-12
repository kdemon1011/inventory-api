"""
OpenEnv-native reward transforms — per-step rewards via observation.reward.

These transforms follow OpenEnv's Transform pattern (from openenv.core.env_server.interfaces).
They take an Observation and return it with the `reward` field populated based on
the step's outcome.

Used when --reward-mode openenv is passed to run_eval.py.
For custom episode-level rewards, see rewards/base.py (unchanged).

Architecture:
    Custom mode  (default):  rewards/base.py  →  RewardCalculator  →  episode-level reward
    OpenEnv mode (--reward-mode openenv):  rewards/transforms/  →  per-step reward + ground truth
"""

from typing import Any, List

from openenv.core.env_server.interfaces import Transform
from openenv.core.env_server.mcp_types import CallToolObservation
from openenv.core.env_server.types import Observation

from rewards.base import RewardBreakdown


class StepRewardTransform(Transform):
    """
    Gym-agnostic per-step reward transform.

    Inspects each observation after a tool call and sets observation.reward:
        - Tool succeeded (no error):  reward = 1.0
        - Tool failed (error):        reward = -0.5
        - Non-tool observation:        reward = 0.0

    Subclass this for gym-specific reward logic (see rewards/transforms/inventory.py).
    """

    def __call__(self, observation: Observation) -> Observation:
        reward = self._compute_reward(observation)
        observation.reward = reward
        return observation

    def _compute_reward(self, observation: Observation) -> float:
        """Compute per-step reward. Override in subclasses for gym-specific logic."""
        if isinstance(observation, CallToolObservation):
            if observation.error is not None:
                return -0.5
            return 1.0
        return 0.0


class OpenEnvRewardCalculator:
    """
    Combines per-step transform rewards with ground truth verification.

    Used as the alternative to RewardCalculator (rewards/base.py) when
    --reward-mode openenv is active.

    Weights:
        Per-step rewards (from transform):  0.40
        Ground truth (from checker):        0.60
    Plus hallucination penalty (-1.0).

    Returns a RewardBreakdown so run_eval.py output stays compatible.
    In the breakdown:
        structural  →  per-step success score (normalized avg of step rewards)
        ground_truth →  ground truth score (same as custom mode)
        efficiency  →  0.0 (not applicable — already captured in step rewards)
        penalty     →  hallucination penalty (same logic as custom mode)
    """

    def __init__(self, w_step: float = 0.40, w_ground_truth: float = 0.60):
        self.w_step = w_step
        self.w_ground_truth = w_ground_truth

    def calculate(
        self,
        step_rewards: List[float],
        outcome_results: List[bool],
    ) -> RewardBreakdown:
        """
        Calculate episode reward from per-step rewards + ground truth.

        Args:
            step_rewards: List of per-step reward values from the transform.
            outcome_results: List of True/False from the gym's ground truth checker.

        Returns:
            RewardBreakdown compatible with run_eval.py display and save.
        """
        # Per-step score: normalize from [-0.5, 1.0] range to [0, 1]
        if step_rewards:
            avg = sum(step_rewards) / len(step_rewards)
            step_score = max(0.0, min(1.0, (avg + 0.5) / 1.5))
        else:
            step_score = 0.0

        # Ground truth score
        if outcome_results:
            gt_score = sum(outcome_results) / len(outcome_results)
        else:
            gt_score = 0.0

        # Hallucination penalty: all steps positive but nothing in DB
        penalty = 0.0
        if step_rewards and outcome_results:
            all_positive = all(r > 0 for r in step_rewards)
            no_outcomes = not any(outcome_results)
            if all_positive and no_outcomes:
                penalty = -1.0

        total = self.w_step * step_score + self.w_ground_truth * gt_score + penalty
        total = max(-1.0, min(1.0, total))

        return RewardBreakdown(
            structural=step_score,
            ground_truth=gt_score,
            efficiency=0.0,
            penalty=penalty,
            total=total,
            details={
                "reward_mode": "openenv",
                "step_rewards": [round(r, 4) for r in step_rewards],
                "avg_step_reward": round(avg, 4) if step_rewards else 0.0,
                "w_step": self.w_step,
                "w_ground_truth": self.w_ground_truth,
            },
        )
