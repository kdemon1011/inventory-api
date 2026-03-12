#!/usr/bin/env python3
"""
Evaluation Runner — run an LLM agent against any gym's scenarios.

This is the main CLI entry point for evaluating LLM models. It:
  1. Connects an LLM (local or online) to an OpenEnv gym
  2. Runs each scenario: LLM reasons → OpenEnv executes → reward scored
  3. Prints per-scenario and aggregate results
  4. Optionally saves results to results/<gym>/<run_id>.md (--save)
  5. Optionally saves detailed trajectory JSON to trajectories/<gym>/<run_id>/<model>.json (--trajectory)

Each evaluation run is grouped under a run ID (auto-generated timestamp or provided via --run-id).
This allows multiple runs to coexist for comparison:
    results/inventory/run_20260311_1830.md    — results for that run
    trajectories/inventory/run_20260311_1830/ — per-model trajectory JSONs

The LLM never calls tools directly — everything goes through OpenEnv.

Usage:
    python run_eval.py --gym inventory --model gpt-4o
    python run_eval.py --gym inventory --model gpt-4o --save --trajectory
    python run_eval.py --gym inventory --model gpt-4o --save --trajectory --run-id run_20260311_1830
    python run_eval.py --gym inventory --model gpt-5.4 --temperature 1.0 --save --trajectory

Before running (pick one):
    Docker:   openenv build inventory/ && docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory
    Local:    cd inventory && python main.py  (Terminal 1)  &&  cd inventory && uv run server  (Terminal 2)
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

# Indian Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

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
        "transform_factory": lambda: _create_inventory_transform(),
        "default_openenv_url": "http://localhost:9000",
        "default_api_url": "http://localhost:8000",
    },
    # ── Demo gym: scaffolded via `openenv init inventory_clone` ──
    "inventory_clone": {
        "scenarios_loader": lambda: _load_inventory_scenarios(),   # reuses inventory scenarios
        "checker_factory": lambda api_url: _create_inventory_clone_checker(),
        "transform_factory": lambda: _create_inventory_transform(),  # reuses inventory transform
        "default_openenv_url": "http://localhost:9001",  # different port from inventory (9000)
        "default_api_url": None,  # in-memory — no separate API
    },
    # Future gyms (each gets its own OpenEnv port):
    # "browser": {
    #     "scenarios_loader": lambda: _load_browser_scenarios(),
    #     "checker_factory": lambda api_url: _create_browser_checker(api_url),
    #     "transform_factory": lambda: _create_browser_transform(),
    #     "default_openenv_url": "http://localhost:9002",
    #     "default_api_url": "http://localhost:8002",
    # },
}


def _load_inventory_scenarios():
    from scenarios.inventory import INVENTORY_SCENARIOS
    return INVENTORY_SCENARIOS


def _create_inventory_checker(api_url):
    from rewards.inventory_checks import InventoryChecker
    return InventoryChecker(api_url=api_url)


def _create_inventory_transform():
    from rewards.transforms.inventory import InventoryStepTransform
    return InventoryStepTransform()


def _create_inventory_clone_checker():
    """
    Placeholder checker for inventory_clone (in-memory, no external API).

    Since the clone stores data in-memory (no persistent DB), ground truth
    checking requires a different approach. For now, returns a no-op checker
    that always passes — the real scoring comes from the OpenEnv transforms.
    """

    class InMemoryChecker:
        def check_all(self, checks):
            return [True] * len(checks)

        def close(self):
            pass

    return InMemoryChecker()


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
    run_id: str = "",
    reward_mode: str = "custom",
):
    """
    Append (or create) a markdown results file for this evaluation run.

    Results are stored at: results/<gym>/<run_id>.md
    If the file already exists, appends a new section for this model run.
    This allows running multiple models within the same run and accumulating results.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    is_new_file = not os.path.exists(output_path)

    with open(output_path, "a") as f:
        if is_new_file:
            f.write(f"# {gym.title()} Gym — Evaluation Results\n\n")
            f.write(f"**Run ID**: `{run_id}`\n\n")
            f.write(f"Evaluation results for the **{gym}** gym across different LLM models.\n\n")
            if reward_mode == "openenv":
                f.write(f"**Reward Mode**: `openenv` — per-step rewards from `rewards/transforms/` + ground truth\n\n")
                f.write(f"Each model is evaluated on the same set of scenarios. ")
                f.write(f"Rewards are computed using OpenEnv transforms:\n")
                f.write(f"- **Step Rewards** (0.40) — per-step success/failure from transform\n")
                f.write(f"- **Ground Truth** (0.60) — database state matches expected outcome\n")
                f.write(f"- **Hallucination Penalty** (-1.0) — tools say success but DB disagrees\n\n")
            else:
                f.write(f"**Reward Mode**: `custom` — episode-level rewards from `rewards/base.py`\n\n")
                f.write(f"Each model is evaluated on the same set of scenarios. ")
                f.write(f"Rewards are computed by `rewards/base.py` using:\n")
                f.write(f"- **Structural** (0.25) — right tools called, no errors\n")
                f.write(f"- **Ground Truth** (0.60) — database state matches expected outcome\n")
                f.write(f"- **Efficiency** (0.15) — solved in reasonable steps\n")
                f.write(f"- **Hallucination Penalty** (-1.0) — tools say success but DB disagrees\n\n")
            f.write(f"Trajectories: `trajectories/{gym}/{run_id}/`\n\n")
            f.write(f"---\n\n")

        safe_model = model.replace("/", "_").replace(":", "_")
        f.write(f"## Model: `{model}`\n\n")
        f.write(f"- **Date**: {timestamp}\n")
        f.write(f"- **Temperature**: {temperature}\n")
        f.write(f"- **Reward Mode**: {reward_mode}\n")
        f.write(f"- **Total Time**: {total_elapsed:.1f}s\n")
        f.write(f"- **Trajectory**: `trajectories/{gym}/{run_id}/{safe_model}.json`\n\n")

        # Results table — headers differ by reward mode
        if reward_mode == "openenv":
            f.write(f"| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |\n")
            f.write(f"|---|:---:|:---:|:---:|:---:|:---:|:---:|\n")
        else:
            f.write(f"| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |\n")
            f.write(f"|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")

        total_reward = 0.0
        for r in results:
            bd = r.get("breakdown")
            if bd:
                if reward_mode == "openenv":
                    f.write(
                        f"| {r['scenario']} "
                        f"| {bd.structural:.2f} "
                        f"| {bd.ground_truth:.2f} "
                        f"| {bd.penalty:.2f} "
                        f"| **{bd.total:.2f}** "
                        f"| {r['steps']} "
                        f"| {r['elapsed']:.1f}s |\n"
                    )
                else:
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
                if reward_mode == "openenv":
                    f.write(
                        f"| {r['scenario']} "
                        f"| — | — | — "
                        f"| **ERROR** "
                        f"| {r['steps']} "
                        f"| {r['elapsed']:.1f}s |\n"
                    )
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


def save_trajectory(
    results: List[Dict[str, Any]],
    scenarios: list,
    model: str,
    gym: str,
    temperature: float,
    total_elapsed: float,
    run_id: str = "",
    reward_mode: str = "custom",
):
    """
    Save a detailed trajectory JSON for this model run.

    Structure:
        trajectories/<gym>/<run_id>/<model_name>.json

    The JSON contains:
      - run metadata (run_id, model, gym, timestamp, temperature, reward_mode)
      - per-scenario trajectories with step-by-step tool calls,
        arguments, results, timestamps, and reward breakdown.
    """
    run_ts = datetime.now(IST).isoformat()

    # Sanitize model name for filename (e.g. "ollama/llama3" → "ollama_llama3")
    safe_model = model.replace("/", "_").replace(":", "_")
    filename = f"{safe_model}.json"

    traj_dir = os.path.join(os.path.dirname(__file__), "trajectories", gym, run_id)
    os.makedirs(traj_dir, exist_ok=True)
    filepath = os.path.join(traj_dir, filename)

    trajectory = {
        "run_id": run_id or "untagged",
        "model": model,
        "gym": gym,
        "timestamp": run_ts,
        "temperature": temperature,
        "reward_mode": reward_mode,
        "total_elapsed_s": round(total_elapsed, 2),
        "total_scenarios": len(results),
        "scenarios": [],
    }

    for r, scenario in zip(results, scenarios):
        scenario_entry = {
            "scenario_id": scenario.id,
            "prompt": scenario.prompt,
            "expected_tools": scenario.expected_tools,
            "max_steps": scenario.max_steps,
            "elapsed_s": round(r["elapsed"], 2),
        }

        # Steps (trajectory detail)
        episode = r.get("episode")
        if episode:
            steps = []
            for i, step in enumerate(episode.steps, 1):
                # Parse result — it's stored as a string now
                result_data = step.result
                if isinstance(result_data, str):
                    try:
                        result_data = json.loads(result_data)
                    except (json.JSONDecodeError, TypeError):
                        pass

                steps.append({
                    "step": i,
                    "timestamp": step.timestamp,
                    "tool_name": step.tool_name,
                    "arguments": step.arguments,
                    "success": step.success,
                    "result": result_data,
                    "error": step.error,
                    "elapsed_s": round(step.elapsed, 3),
                })
            scenario_entry["steps"] = steps
            scenario_entry["total_steps"] = len(steps)
        else:
            scenario_entry["steps"] = []
            scenario_entry["total_steps"] = 0
            scenario_entry["error"] = r.get("error", "Unknown error")

        # Outcome checks
        outcome_results = r.get("outcome_results", [])
        checks = []
        for check_def, passed in zip(scenario.outcome_checks, outcome_results):
            checks.append({
                "check": check_def,
                "passed": passed,
            })
        scenario_entry["outcome_checks"] = checks

        # Reward breakdown
        bd = r.get("breakdown")
        if bd:
            scenario_entry["reward"] = {
                "structural": round(bd.structural, 4),
                "ground_truth": round(bd.ground_truth, 4),
                "efficiency": round(bd.efficiency, 4),
                "penalty": round(bd.penalty, 4),
                "total": round(bd.total, 4),
            }
        else:
            scenario_entry["reward"] = None

        trajectory["scenarios"].append(scenario_entry)

    # Compute run-level summary
    totals = [s["reward"]["total"] for s in trajectory["scenarios"] if s.get("reward")]
    trajectory["avg_reward"] = round(sum(totals) / len(totals), 4) if totals else 0.0

    with open(filepath, "w") as f:
        json.dump(trajectory, f, indent=2, default=str)

    print(f"\n  Trajectory saved: {filepath}")
    logger.info(f"Trajectory saved to {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate an LLM agent against OpenEnv gym scenarios.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_eval.py --gym inventory --model gpt-4o
  python run_eval.py --gym inventory --model gpt-4o --reward-mode openenv
  python run_eval.py --gym inventory --model claude-sonnet-4-6
  python run_eval.py --gym inventory --model ollama/llama3
  python run_eval.py --gym inventory --model gpt-4o --scenario create_product
  python run_eval.py --gym inventory --model gpt-4o --save
  python run_eval.py --gym inventory --model gpt-4o --trajectory
  python run_eval.py --gym inventory --model gpt-4o --save --trajectory
  python run_eval.py --gym inventory --model gpt-5.4 --temperature 1.0 --save --trajectory
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
        "--trajectory",
        action="store_true",
        help="Save detailed trajectory JSON to trajectories/<gym>/<run_id>/",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run identifier for grouping results and trajectories "
             "(default: auto-generated as run_YYYYMMDD_HHMM)",
    )
    parser.add_argument(
        "--reward-mode",
        default="custom",
        choices=["custom", "openenv"],
        help="Reward mode: 'custom' (episode-level from rewards/base.py) "
             "or 'openenv' (per-step from rewards/transforms/). Default: custom",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Generate or use provided run_id
    if args.run_id:
        run_id = args.run_id
    else:
        run_id = f"run_{datetime.now(IST).strftime('%Y%m%d_%H%M')}"

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
    print(f"  Run ID:       {run_id}")
    print(f"  OpenEnv URL:  {openenv_url}")
    print(f"  API URL:      {api_url}")
    print(f"  Scenarios:    {len(scenarios)} of {len(all_scenarios)}")
    print(f"  Temperature:  {args.temperature}")
    print(f"  Reward Mode:  {args.reward_mode}")

    # Create gym-specific transform (only needed for openenv reward mode)
    transform = None
    if args.reward_mode == "openenv":
        transform = gym_config["transform_factory"]()

    # Create agent runner
    runner = AgentRunner(
        model=args.model,
        openenv_url=openenv_url,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        reward_mode=args.reward_mode,
        transform=transform,
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
                    "episode": episode,
                    "outcome_results": outcome_results,
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
            os.path.dirname(__file__), "results", args.gym, f"{run_id}.md"
        )
        save_results_to_markdown(
            results=results,
            model=args.model,
            gym=args.gym,
            output_path=output_path,
            total_elapsed=total_elapsed,
            temperature=args.temperature,
            run_id=run_id,
            reward_mode=args.reward_mode,
        )
        print(f"\n  Results saved: {output_path}")

    # Save trajectory JSON if requested
    if args.trajectory:
        save_trajectory(
            results=results,
            scenarios=scenarios,
            model=args.model,
            gym=args.gym,
            temperature=args.temperature,
            total_elapsed=total_elapsed,
            run_id=run_id,
            reward_mode=args.reward_mode,
        )


def _short_json(obj, max_len=80):
    """Compact JSON string, truncated if too long."""
    s = json.dumps(obj, default=str)
    return s if len(s) <= max_len else s[:max_len] + "..."


if __name__ == "__main__":
    main()
