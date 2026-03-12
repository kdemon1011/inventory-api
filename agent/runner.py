"""
Gym-agnostic Agent Runner — connects an LLM to any OpenEnv environment.

This module is the CORE of the evaluation platform. It:
  1. Connects to an OpenEnv server (any gym)
  2. Discovers tools via list_tools()
  3. Gives the LLM a scenario prompt + available tools
  4. Loops: LLM reasons → agent calls env.step() → observation → LLM reasons again
  5. Collects an EpisodeLog with timestamps for reward calculation + trajectory logging

The runner does NOT know about specific gyms. It only knows OpenEnv.
The same runner works for inventory, browser, or any future gym.

Each tool call is timestamped and timed so trajectory data can be exported
for debugging and analysis (see run_eval.py --trajectory).

Usage:
    runner = AgentRunner(model="gpt-4o", openenv_url="http://localhost:9000")
    episode, breakdown = runner.run_scenario(scenario, checker)
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta

# Indian Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))
from typing import Any, Dict, List, Optional, Tuple

from openenv.core.mcp_client import MCPToolClient
from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation, Tool

from rewards.base import (
    EpisodeLog,
    RewardBreakdown,
    RewardCalculator,
    Scenario,
)
from .llm import LLMClient

logger = logging.getLogger(__name__)


# ── System Prompt ──
# This is gym-agnostic: it tells the LLM HOW to behave, not WHAT tools exist.
# The tools come from OpenEnv's list_tools() dynamically.

SYSTEM_PROMPT = """\
You are an AI agent interacting with an environment through tools.

Your job:
1. Read the task description carefully.
2. Use the available tools to complete the task.
3. Call tools one at a time. Wait for each result before deciding the next step.
4. When the task is complete, respond with a plain text summary of what you did.
   Do NOT call any more tools after you're done.

Rules:
- Only use tools that are listed as available.
- Provide all required arguments for each tool call.
- If a tool call fails, read the error and decide how to recover.
- Be efficient — complete the task in as few steps as possible.
- When you're done, clearly state what you accomplished.
"""


def mcp_tools_to_openai(tools: List[Tool]) -> List[Dict[str, Any]]:
    """
    Convert OpenEnv MCP tool definitions to OpenAI function-calling format.

    OpenEnv Tool:
        Tool(name="create_product", description="...", input_schema={...})

    OpenAI format:
        {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}

    This conversion lets ANY LLM (via LiteLLM) understand the tools that
    a specific gym exposes, without knowing anything about the gym itself.
    """
    openai_tools = []
    for tool in tools:
        schema = tool.input_schema or {"type": "object", "properties": {}}
        # Ensure the schema has the required top-level fields
        if "type" not in schema:
            schema["type"] = "object"
        if "properties" not in schema:
            schema["properties"] = {}

        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": schema,
            },
        })
    return openai_tools


def _observation_to_str(step_result) -> str:
    """Convert an OpenEnv step result to a string the LLM can read."""
    obs = step_result.observation
    if isinstance(obs, CallToolObservation):
        if obs.error:
            return json.dumps({"error": obs.error.message}, indent=2)
        # The result can be various types — serialize to string
        result = obs.result
        if hasattr(result, "data"):
            result = result.data
        elif isinstance(result, dict) and "data" in result:
            result = result["data"]
        try:
            return json.dumps(result, indent=2, default=str)
        except (TypeError, ValueError):
            return str(result)
    # Fallback for other observation types
    if hasattr(obs, "metadata") and obs.metadata:
        return json.dumps(obs.metadata, indent=2, default=str)
    return str(obs)


class AgentRunner:
    """
    Gym-agnostic agent that connects an LLM to any OpenEnv environment.

    The runner:
      - Connects to OpenEnv (any gym)
      - Discovers tools dynamically
      - Lets the LLM decide which tools to call
      - Routes all actions through OpenEnv (never calls tools directly)
      - Collects logs for reward calculation

    Reward modes:
      - "custom"  (default): Episode-level reward via RewardCalculator (rewards/base.py)
      - "openenv": Per-step reward via Transform (rewards/transforms/) + ground truth

    Args:
        model: LiteLLM model string (e.g., "gpt-4o", "ollama/llama3")
        openenv_url: URL of the OpenEnv server (e.g., "http://localhost:9000")
        temperature: LLM sampling temperature (0.0 = deterministic)
        max_tokens: Max tokens per LLM response
        reward_mode: "custom" or "openenv"
        transform: StepRewardTransform instance (required when reward_mode="openenv")
    """

    def __init__(
        self,
        model: str,
        openenv_url: str = "http://localhost:9000",
        temperature: float = 0.0,
        max_tokens: int = 1024,
        reward_mode: str = "custom",
        transform=None,
    ):
        self.llm = LLMClient(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.openenv_url = openenv_url
        self.reward_mode = reward_mode
        self.transform = transform

        # Custom mode: episode-level reward from rewards/base.py
        self.calculator = RewardCalculator()

        # OpenEnv mode: per-step reward from transforms + ground truth
        if reward_mode == "openenv":
            from rewards.transforms.base import OpenEnvRewardCalculator
            self.openenv_calculator = OpenEnvRewardCalculator()

    def run_scenario(
        self,
        scenario: Scenario,
        checker: Any,
        env: Optional[MCPToolClient] = None,
    ) -> Tuple[EpisodeLog, RewardBreakdown]:
        """
        Run a single scenario through the LLM agent.

        Flow:
          1. env.reset()
          2. env.list_tools() → convert to LLM format
          3. Build messages: system prompt + scenario prompt
          4. Loop (up to max_steps):
             a. LLM decides what tool to call
             b. env.step(CallToolAction(...))
             c. Feed observation back to LLM
             d. If LLM responds with text (no tool call) → done
          5. Verify outcomes against ground truth (checker)
          6. Calculate reward

        Args:
            scenario: The task definition with prompt, expected tools, outcome checks.
            checker: Gym-specific checker (e.g., InventoryChecker) with check_all().
            env: Optional pre-connected OpenEnv client. If None, creates one.

        Returns:
            (EpisodeLog, RewardBreakdown) — the full record + scored result.
        """
        own_env = env is None
        if own_env:
            env = MCPToolClient(base_url=self.openenv_url)
            env.__enter__()

        try:
            return self._execute(scenario, checker, env)
        finally:
            if own_env:
                env.__exit__(None, None, None)

    def _execute(
        self,
        scenario: Scenario,
        checker: Any,
        env: MCPToolClient,
    ) -> Tuple[EpisodeLog, RewardBreakdown]:
        """Internal: run the agent loop and calculate reward."""

        # 1. Reset environment
        env.reset()

        # 2. Discover tools from OpenEnv
        tools = env.list_tools(use_cache=False)
        openai_tools = mcp_tools_to_openai(tools)
        tool_names = [t.name for t in tools]
        logger.info(f"Discovered {len(tools)} tools: {tool_names}")

        # 3. Build initial messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": scenario.prompt},
        ]

        # 4. Agent loop
        episode = EpisodeLog()
        step_rewards = []  # Per-step rewards (used in openenv mode only)
        final_answer = None

        for step_num in range(1, scenario.max_steps + 1):
            logger.info(f"Step {step_num}/{scenario.max_steps}")

            # Ask LLM what to do
            response = self.llm.chat(messages, tools=openai_tools)
            tool_calls = LLMClient.extract_tool_calls(response)

            if not tool_calls:
                # LLM responded with text — it thinks it's done
                final_answer = LLMClient.get_text_response(response)
                logger.info(f"Agent done. Final answer: {(final_answer or '')[:100]}...")
                break

            # Add assistant message (with tool_calls) to conversation
            messages.append(response.choices[0].message.model_dump())

            # Execute each tool call through OpenEnv
            for tc in tool_calls:
                tool_name = tc["name"]
                arguments = tc["arguments"]
                call_id = tc["id"]

                logger.info(f"  Tool: {tool_name}({json.dumps(arguments, default=str)[:100]})")

                # Route through OpenEnv — NOT directly to the tool
                step_ts = datetime.now(IST).isoformat()
                step_start = time.time()
                error_msg = None
                try:
                    step_result = env.step(
                        CallToolAction(tool_name=tool_name, arguments=arguments)
                    )
                    obs = step_result.observation
                    is_error = (
                        isinstance(obs, CallToolObservation)
                        and obs.error is not None
                    )
                    result_str = _observation_to_str(step_result)
                    if is_error and isinstance(obs, CallToolObservation):
                        error_msg = obs.error.message
                except Exception as exc:
                    is_error = True
                    error_msg = str(exc)
                    result_str = json.dumps({"error": error_msg})
                    obs = None

                step_elapsed = time.time() - step_start

                # OpenEnv mode: apply transform to get per-step reward
                if self.reward_mode == "openenv" and self.transform and obs is not None:
                    transformed = self.transform(obs)
                    step_rewards.append(
                        transformed.reward if transformed.reward is not None else 0.0
                    )

                # Log the step (with timestamp + elapsed for trajectory)
                episode.add_step(
                    tool_name=tool_name,
                    arguments=arguments,
                    success=not is_error,
                    result=result_str,  # store the serialized result string
                    error=error_msg,
                    timestamp=step_ts,
                    elapsed=step_elapsed,
                )

                logger.info(f"    → success={not is_error} ({step_elapsed:.2f}s)")

                # Feed result back to LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result_str,
                })

        # 5. Verify outcomes against ground truth
        outcome_results = checker.check_all(scenario.outcome_checks)

        # 6. Calculate reward — mode determines which calculator is used
        if self.reward_mode == "openenv":
            breakdown = self.openenv_calculator.calculate(
                step_rewards=step_rewards,
                outcome_results=outcome_results,
            )
        else:
            breakdown = self.calculator.calculate(
                episode=episode,
                scenario=scenario,
                outcome_results=outcome_results,
            )

        return episode, breakdown
