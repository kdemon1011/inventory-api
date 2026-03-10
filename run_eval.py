#!/usr/bin/env python3
"""
Evaluation Runner — run an LLM agent against any gym's scenarios.

This is the main entry point for evaluating LLM models. It:
  1. Connects an LLM (local or online) to an OpenEnv gym
  2. Runs each scenario: LLM reasons → OpenEnv executes → reward scored
  3. Prints per-scenario and aggregate results
  4. Optionally saves results to a markdown file

The LLM never calls tools directly — everything goes through OpenEnv.

Usage:
    # Evaluate with OpenAI GPT-4o on the inventory gym
    python run_eval.py --gym inventory --model gpt-4o

    # Evaluate with Anthropic Claude
    python run_eval.py --gym inventory --model claude-sonnet-4-20250514

    # Evaluate with local Ollama model
    python run_eval.py --gym inventory --model ollama/llama3

    # Run a specific scenario only
    python run_eval.py --gym inventory --model gpt-4o --scenario create_product

    # Save results to markdown
    python run_eval.py --gym inventory --model gpt-4o --save

Before running:
    Terminal 1: cd inventory && python main.py          (API on port 8000)
    Terminal 2: cd inventory && python server/app.py    (OpenEnv on port 9000)
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv

# Load root .env for API keys and model config
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.runner import AgentRunner
from rewards.base import RewardBreakdown

logger = logging.getLogger(__name__)


# ── Gym Registry ──
# Maps gym names to their configurations.
# To add a new gym: add an entry here with its scenarios, checker, and defaults.

GYM_REGISTRY = {
    "inventory": {
        "scenarios_loader": lambda: _load_inventory_scenarios(),
        "checker_factory": lambda api_url: _create_inventory_checker(api_url),
        "default_openenv_url": "http://localhost:9000",
        "default_api_url": "http://localhost:8000",
    },
    # Future gyms:
    # "browser": {
    #     "scenarios_loader": lambda: _load_browser_scenarios(),
    #     "checker_factory": lambda api_url: _create_browser_checker(api_url),
    #     "default_openenv_url": "http://localhost:9001",
    #     "default_api_url": "http://localhost:8001",
    # },
}


def _load_inventory_scenarios():
    from scenarios.inventory import INVENTORY_SCENARIOS
    return INVENTORY_SCENARIOS


def _create_inventory_checker(api_url):
    from rewards.inventory_checks import InventoryChecker
    return InventoryChecker(api_url=api_url)


def divider(text: str = ""):
    print(f"\n{'=' * 70}")
    if text:
        print(f"  {text}")
        print(f"{'=' * 70}")


def print_breakdown(breakdown: RewardBreakdown):
    """Print a formatted reward breakdown."""
    print(breakdown.summary())
    print()
    print(f"  Details: {breakdown.details}")


def save_results_to_markdown(
    results: List[Dict[str, Any]],
    model: str,
    gym: str,
    output_path: str,
    total_elapsed: float,
    temperature: float,
):
    """
    Append (or create) a markdown results file for this gym.

    If the file already exists, appends a new section for this model run.
    This allows running multiple models and accumulating results in one file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_new_file = not os.path.exists(output_path)

    with open(output_path, "a") as f:
        if is_new_file:
            f.write(f"# {gym.title()} Gym — Evaluation Results\n\n")
            f.write(f"Evaluation results for the **{gym}** gym across different LLM models.\n\n")
            f.write(f"Each model is evaluated on the same set of scenarios. ")
            f.write(f"Rewards are computed by `rewards/base.py` using:\n")
            f.write(f"- **Structural** (0.25) — right tools called, no errors\n")
            f.write(f"- **Ground Truth** (0.60) — database state matches expected outcome\n")
            f.write(f"- **Efficiency** (0.15) — solved in reasonable steps\n")
            f.write(f"- **Hallucination Penalty** (-1.0) — tools say success but DB disagrees\n\n")
            f.write(f"---\n\n")

        f.write(f"## Model: `{model}`\n\n")
        f.write(f"- **Date**: {timestamp}\n")
        f.write(f"- **Temperature**: {temperature}\n")
        f.write(f"- **Total Time**: {total_elapsed:.1f}s\n\n")

        # Results table
        f.write(f"| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |\n")
        f.write(f"|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")

        total_reward = 0.0
        for r in results:
            bd = r.get("breakdown")
            if bd:
                f.write(
                    f"| {r['scenario']} "
                    f"| {bd.structural:.2f} "
                    f"| {bd.ground_truth:.2f} "
                    f"| {bd.efficiency:.2f} "
                    f"| {bd.penalty:.2f} "
                    f"| **{bd.total:.2f}** "
                    f"| {r['steps']} "
                    f"| {r['elapsed']:.1f}s |\n"
                )
                total_reward += bd.total
            else:
                f.write(
                    f"| {r['scenario']} "
                    f"| — | — | — | — "
                    f"| **ERROR** "
                    f"| {r['steps']} "
                    f"| {r['elapsed']:.1f}s |\n"
                )

        avg = total_reward / len(results) if results else 0.0
        f.write(f"\n**Average Reward: {avg:.2f}**\n\n")
        f.write(f"---\n\n")

    logger.info(f"Results saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate an LLM agent against OpenEnv gym scenarios.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_eval.py --gym inventory --model gpt-4o
  python run_eval.py --gym inventory --model claude-sonnet-4-20250514
  python run_eval.py --gym inventory --model ollama/llama3
  python run_eval.py --gym inventory --model gpt-4o --scenario create_product
  python run_eval.py --gym inventory --model gpt-4o --save
        """,
    )
    parser.add_argument(
        "--gym",
        required=True,
        choices=list(GYM_REGISTRY.keys()),
        help="Which gym to evaluate against",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", "gpt-4o"),
        help="LiteLLM model string (default: $LLM_MODEL or gpt-4o)",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="Run a specific scenario by ID (default: run all)",
    )
    parser.add_argument(
        "--openenv-url",
        default=None,
        help="OpenEnv server URL (default: from gym config)",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        help="Gym API URL for ground truth checks (default: from gym config)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=float(os.getenv("LLM_TEMPERATURE", "0.0")),
        help="LLM sampling temperature (default: 0.0)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.getenv("LLM_MAX_TOKENS", "1024")),
        help="Max tokens per LLM response (default: 1024)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to results/<gym>.md",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load gym config
    gym_config = GYM_REGISTRY[args.gym]
    openenv_url = args.openenv_url or gym_config["default_openenv_url"]
    api_url = args.api_url or gym_config["default_api_url"]

    # Load scenarios
    all_scenarios = gym_config["scenarios_loader"]()
    if args.scenario:
        scenarios = [s for s in all_scenarios if s.id == args.scenario]
        if not scenarios:
            available = [s.id for s in all_scenarios]
            print(f"Error: Scenario '{args.scenario}' not found. Available: {available}")
            sys.exit(1)
    else:
        scenarios = all_scenarios

    # Print header
    divider("LLM Evaluation Run")
    print(f"  Gym:          {args.gym}")
    print(f"  Model:        {args.model}")
    print(f"  OpenEnv URL:  {openenv_url}")
    print(f"  API URL:      {api_url}")
    print(f"  Scenarios:    {len(scenarios)} of {len(all_scenarios)}")
    print(f"  Temperature:  {args.temperature}")

    # Create agent runner
    runner = AgentRunner(
        model=args.model,
        openenv_url=openenv_url,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    # Create gym-specific checker
    checker = gym_config["checker_factory"](api_url)

    # Run scenarios
    results = []
    total_start = time.time()

    try:
        for i, scenario in enumerate(scenarios, 1):
            divider(f"Scenario {i}/{len(scenarios)}: {scenario.id}")
            print(f"  Prompt: {scenario.prompt[:120]}...")
            print(f"  Expected tools: {scenario.expected_tools}")
            print(f"  Max steps: {scenario.max_steps}")
            print()

            start = time.time()
            try:
                episode, breakdown = runner.run_scenario(scenario, checker)
                elapsed = time.time() - start

                print()
                print("  — Agent Actions —")
                for step in episode.steps:
                    status = "✅" if step.success else "❌"
                    args_str = _short_json(step.arguments)
                    print(f"  {status} {step.tool_name}({args_str})")
                print(f"  Steps taken: {len(episode.steps)}")

                print()
                print("  — Ground Truth Verification —")
                outcome_results = checker.check_all(scenario.outcome_checks)
                for check, passed in zip(scenario.outcome_checks, outcome_results):
                    status = "✅" if passed else "❌"
                    label = check.get("field", check.get("sku", check.get("customer_email", check["type"])))
                    print(f"  {status} {check['type']}: {label}")

                print()
                print("  — Reward Breakdown —")
                print_breakdown(breakdown)
                print(f"\n  ⏱  Completed in {elapsed:.1f}s")

                results.append({
                    "scenario": scenario.id,
                    "total_reward": breakdown.total,
                    "breakdown": breakdown,
                    "steps": len(episode.steps),
                    "elapsed": elapsed,
                })

            except Exception as e:
                elapsed = time.time() - start
                print(f"\n  ❌ ERROR: {e}")
                logger.exception(f"Scenario {scenario.id} failed")
                results.append({
                    "scenario": scenario.id,
                    "total_reward": 0.0,
                    "breakdown": None,
                    "steps": 0,
                    "elapsed": elapsed,
                    "error": str(e),
                })

    finally:
        # Clean up checker
        if hasattr(checker, "close"):
            checker.close()

    # Print summary
    total_elapsed = time.time() - total_start
    divider("Evaluation Summary")
    print(f"  Model:    {args.model}")
    print(f"  Gym:      {args.gym}")
    print(f"  Time:     {total_elapsed:.1f}s")
    print()

    print(f"  {'Scenario':<30} {'Reward':>8} {'Steps':>6} {'Time':>6}")
    print(f"  {'─' * 30} {'─' * 8} {'─' * 6} {'─' * 6}")

    total_reward = 0.0
    for r in results:
        reward_str = f"{r['total_reward']:.2f}" if r.get("breakdown") else "ERROR"
        print(f"  {r['scenario']:<30} {reward_str:>8} {r['steps']:>6} {r['elapsed']:>5.1f}s")
        total_reward += r["total_reward"]

    avg_reward = total_reward / len(results) if results else 0.0
    print(f"  {'─' * 30} {'─' * 8} {'─' * 6} {'─' * 6}")
    print(f"  {'AVERAGE':<30} {avg_reward:>8.2f}")
    print()

    # Save results to markdown if requested
    if args.save:
        output_path = os.path.join(
            os.path.dirname(__file__), "results", f"{args.gym}.md"
        )
        save_results_to_markdown(
            results=results,
            model=args.model,
            gym=args.gym,
            output_path=output_path,
            total_elapsed=total_elapsed,
            temperature=args.temperature,
        )


def _short_json(obj, max_len=80):
    """Compact JSON string, truncated if too long."""
    s = json.dumps(obj, default=str)
    return s if len(s) <= max_len else s[:max_len] + "..."


if __name__ == "__main__":
    main()
