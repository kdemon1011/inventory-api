"""
Base reward calculator — reusable across any OpenEnv gym.

Computes a 4-component episode-level reward:
  1. Structural   (0.20) — right tools called, no errors
  2. Ground Truth (0.45) — actual state matches expected outcome
  3. Consistency  (0.25) — tool results match verified state
  4. Efficiency   (0.10) — solved in reasonable number of steps

Usage:
    calculator = RewardCalculator()
    breakdown = calculator.calculate(episode_log, scenario, outcome_results)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


# ── Data Classes ──


@dataclass
class StepLog:
    """Record of a single tool call made by the agent."""

    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    result: Any = None
    error: Optional[str] = None


@dataclass
class EpisodeLog:
    """Record of all tool calls in one episode."""

    steps: List[StepLog] = field(default_factory=list)

    def add_step(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
    ) -> None:
        self.steps.append(
            StepLog(
                tool_name=tool_name,
                arguments=arguments,
                success=success,
                result=result,
                error=error,
            )
        )

    @property
    def tools_used(self) -> List[str]:
        return [s.tool_name for s in self.steps]

    @property
    def tools_used_set(self) -> Set[str]:
        return set(self.tools_used)


@dataclass
class Scenario:
    """
    Definition of a task for the agent.

    Each gym defines its own scenarios. The reward calculator
    doesn't care about the domain — it only needs the fields below.
    """

    id: str
    prompt: str
    expected_tools: List[str]
    max_steps: int
    outcome_checks: List[Dict[str, Any]]


@dataclass
class RewardBreakdown:
    """Detailed reward breakdown — useful for debugging and logging."""

    structural: float = 0.0
    ground_truth: float = 0.0
    consistency: float = 0.0
    efficiency: float = 0.0
    penalty: float = 0.0
    total: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"  Structural:   {self.structural:.2f}  (weight 0.20)",
            f"  Ground Truth: {self.ground_truth:.2f}  (weight 0.45)",
            f"  Consistency:  {self.consistency:.2f}  (weight 0.25)",
            f"  Efficiency:   {self.efficiency:.2f}  (weight 0.10)",
        ]
        if self.penalty < 0:
            lines.append(f"  Penalty:      {self.penalty:.2f}  (hallucination)")
        lines.append(f"  ────────────────────────")
        lines.append(f"  TOTAL:        {self.total:.2f}")
        return "\n".join(lines)


# ── Reward Calculator ──


class RewardCalculator:
    """
    Computes episode-level reward from logs + scenario + verification results.

    This class is gym-agnostic. Each gym provides:
      - An EpisodeLog (what the agent did)
      - A Scenario (what the agent should have done)
      - outcome_results: List[bool] from the gym's own checker
      - consistency_score: float from comparing tool results vs DB

    Weights are configurable per gym.
    """

    def __init__(
        self,
        w_structural: float = 0.20,
        w_ground_truth: float = 0.45,
        w_consistency: float = 0.25,
        w_efficiency: float = 0.10,
    ):
        self.w_structural = w_structural
        self.w_ground_truth = w_ground_truth
        self.w_consistency = w_consistency
        self.w_efficiency = w_efficiency

    def calculate(
        self,
        episode: EpisodeLog,
        scenario: Scenario,
        outcome_results: List[bool],
        consistency_score: float = 1.0,
    ) -> RewardBreakdown:
        """
        Calculate the full reward breakdown.

        Args:
            episode: Log of all tool calls the agent made.
            scenario: The task definition with expected tools and outcomes.
            outcome_results: List of True/False from running each outcome check.
            consistency_score: 0-1 score from consistency verification.
                               Defaults to 1.0 (skip) when no LLM is connected yet.
        """
        breakdown = RewardBreakdown()

        breakdown.structural = self._structural_score(episode, scenario)
        breakdown.ground_truth = self._ground_truth_score(outcome_results)
        breakdown.consistency = consistency_score
        breakdown.efficiency = self._efficiency_score(episode, scenario)
        breakdown.penalty = self._hallucination_penalty(episode, outcome_results)

        breakdown.total = (
            self.w_structural * breakdown.structural
            + self.w_ground_truth * breakdown.ground_truth
            + self.w_consistency * breakdown.consistency
            + self.w_efficiency * breakdown.efficiency
            + breakdown.penalty
        )
        breakdown.total = max(-1.0, min(1.0, breakdown.total))

        breakdown.details = {
            "tools_expected": scenario.expected_tools,
            "tools_used": episode.tools_used,
            "outcome_checks_passed": sum(outcome_results),
            "outcome_checks_total": len(outcome_results),
            "steps_taken": len(episode.steps),
            "max_steps": scenario.max_steps,
        }

        return breakdown

    def _structural_score(self, episode: EpisodeLog, scenario: Scenario) -> float:
        """F1 score of tool selection + execution success rate."""
        if not episode.steps:
            return 0.0

        expected = set(scenario.expected_tools)
        used = episode.tools_used_set

        # F1 of tool selection
        intersection = expected & used
        precision = len(intersection) / len(used) if used else 0.0
        recall = len(intersection) / len(expected) if expected else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        # Execution success rate
        success_rate = sum(1 for s in episode.steps if s.success) / len(episode.steps)

        return 0.6 * f1 + 0.4 * success_rate

    def _ground_truth_score(self, outcome_results: List[bool]) -> float:
        """Fraction of outcome checks that passed."""
        if not outcome_results:
            return 0.0
        return sum(outcome_results) / len(outcome_results)

    def _efficiency_score(self, episode: EpisodeLog, scenario: Scenario) -> float:
        """Ratio of expected steps to actual steps (capped at 1.0)."""
        if not episode.steps:
            return 0.0
        expected = len(scenario.expected_tools)
        actual = len(episode.steps)
        return min(expected / actual, 1.0)

    def _hallucination_penalty(
        self, episode: EpisodeLog, outcome_results: List[bool]
    ) -> float:
        """
        Hard penalty: agent thinks everything succeeded but DB shows nothing.
        This is the clearest sign of hallucination.
        """
        if not episode.steps or not outcome_results:
            return 0.0

        all_calls_succeeded = all(s.success for s in episode.steps)
        no_outcomes_passed = not any(outcome_results)

        if all_calls_succeeded and no_outcomes_passed:
            return -1.0

        return 0.0
