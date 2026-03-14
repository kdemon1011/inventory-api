#!/usr/bin/env python3
"""
Evaluation Runner — run an LLM agent against any gym's scenarios.

This is the main CLI entry point for evaluating LLM models. It:
  1. Discovers & connects to any gym via AutoEnv (auto-discovery)
  2. Runs each scenario: LLM reasons → OpenEnv executes → reward scored
  3. Prints per-scenario and aggregate results
  4. Optionally saves results to results/<gym>/<run_id>.md (--save)
  5. Optionally saves detailed trajectory JSON to trajectories/<gym>/<run_id>/<model>.json (--trajectory)

Connection is handled entirely by AutoEnv — no manual URLs required.
AutoEnv discovers the gym from pip-installed packages (pip install -e inventory/).

Supports two execution modes:
  - Sequential (default): one model at a time, backward-compatible
  - Parallel (--parallel N): run N models simultaneously, each with isolated DB sessions

Prerequisites:
    1. Install the gym:  pip install -e inventory/   (or browser/, payment_gateway/, etc.)
    2. Start the gym:    docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory
    3. Run evaluation:   python run_eval.py --gym inventory --model gpt-4o

Usage:
    # Sequential (one model)
    python run_eval.py --gym inventory --model gpt-4o --save --trajectory

    # Parallel (multiple models, comma-separated)
    python run_eval.py --gym inventory --model gpt-4o-mini,gpt-4o,claude-sonnet-4-6 --parallel 3 --save --trajectory

    # Browser gym (Node.js + React e-commerce app)
    python run_eval.py --gym browser --model gpt-5.4 --save --trajectory
    python run_eval.py --gym browser --model gpt-5.4,claude-sonnet-4-6,claude-opus-4-6 --parallel 3 --reward-mode openenv

    # More examples
    python run_eval.py --gym inventory --model gpt-4o --reward-mode openenv
    python run_eval.py --gym inventory --model gpt-4o --scenario create_product
    python run_eval.py --gym inventory --model gpt-5.4 --temperature 1.0 --save --trajectory
"""

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

# Indian Standard Time (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

from dotenv import load_dotenv

# Load root .env for API keys and model config
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openenv import AutoEnv

from agent.runner import AgentRunner
from rewards.base import RewardBreakdown

logger = logging.getLogger(__name__)


# ── Gym Registry ──
# Maps gym names to their configurations.
# To add a new gym: pip install -e <gym>/ and add an entry here.
#
# Connection is fully via AutoEnv — base_url is auto-derived from openenv.yaml port.
# The only gym-specific config left is the API URL for ground truth checking
# (NOT an OpenEnv concept — it's our evaluation infrastructure).

GYM_REGISTRY = {
    "inventory": {
        "scenarios_loader": lambda: _load_inventory_scenarios(),
        "checker_factory": lambda api_url, session_id=None: _create_inventory_checker(api_url, session_id),
        "transform_factory": lambda: _create_inventory_transform(),
        "default_api_url": "http://localhost:8000",   # for ground truth checker (not OpenEnv)
    },
    # Future gyms — uncomment as each is implemented:
    # "payment_gateway": {
    #     "scenarios_loader": lambda: _load_payment_scenarios(),
    #     "checker_factory": lambda api_url, session_id=None: _create_payment_checker(api_url, session_id),
    #     "transform_factory": lambda: _create_payment_transform(),
    #     "default_api_url": "http://localhost:8002",
    # },
    "browser": {
        "scenarios_loader": lambda: _load_browser_scenarios(),
        "checker_factory": lambda api_url, session_id=None: _create_browser_checker(api_url, session_id),
        "transform_factory": lambda: _create_browser_transform(),
        "default_api_url": "http://localhost:8003",
    },
    # "code_judge": {
    #     "scenarios_loader": lambda: _load_code_judge_scenarios(),
    #     "checker_factory": lambda api_url, session_id=None: _create_code_judge_checker(api_url, session_id),
    #     "transform_factory": lambda: _create_code_judge_transform(),
    #     "default_api_url": "http://localhost:8004",
    # },
    # "cloud_infra": {
    #     "scenarios_loader": lambda: _load_cloud_infra_scenarios(),
    #     "checker_factory": lambda api_url, session_id=None: _create_cloud_infra_checker(api_url, session_id),
    #     "transform_factory": lambda: _create_cloud_infra_transform(),
    #     "default_api_url": "http://localhost:8005",
    # },
}


def _resolve_base_url(gym_name: str) -> str:
    """
    Derive the OpenEnv server base_url from the installed gym's openenv.yaml port.

    AutoEnv knows the gym package → we read openenv.yaml from it → extract port.
    No hardcoded URLs needed in GYM_REGISTRY.
    """
    import importlib.resources
    import yaml

    try:
        ref = importlib.resources.files(gym_name).joinpath("openenv.yaml")
        with importlib.resources.as_file(ref) as f:
            manifest = yaml.safe_load(f.read_text())
            port = manifest.get("port", 9000)
            return f"http://localhost:{port}"
    except Exception:
        # Fallback: default OpenEnv port
        logger.warning(f"Could not read openenv.yaml for '{gym_name}', defaulting to port 9000")
        return "http://localhost:9000"


def _load_inventory_scenarios():
    from scenarios.inventory import INVENTORY_SCENARIOS
    return INVENTORY_SCENARIOS


def _create_inventory_checker(api_url, session_id=None):
    from rewards.inventory_checks import InventoryChecker
    return InventoryChecker(api_url=api_url, session_id=session_id)


def _create_inventory_transform():
    from rewards.transforms.inventory import InventoryStepTransform
    return InventoryStepTransform()


def _load_browser_scenarios():
    from scenarios.browser import BROWSER_SCENARIOS
    return BROWSER_SCENARIOS


def _create_browser_checker(api_url, session_id=None):
    from rewards.browser_checks import BrowserChecker
    return BrowserChecker(api_url=api_url, session_id=session_id)


def _create_browser_transform():
    from rewards.transforms.browser import BrowserStepTransform
    return BrowserStepTransform()


def _fetch_gym_metadata(base_url: str) -> dict | None:
    """
    Fetch EnvironmentMetadata from the running OpenEnv server's /metadata endpoint.

    Returns the metadata dict or None if the server is unreachable.
    The readme_content field is excluded from the return to keep output manageable.
    """
    import httpx

    try:
        resp = httpx.get(f"{base_url}/metadata", timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        # Drop readme_content — it's the full README, too large for display
        data.pop("readme_content", None)
        return data
    except Exception as e:
        logger.debug(f"Failed to fetch /metadata from {base_url}: {e}")
        return None


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
    gym_version: str = "unknown",
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
            f.write(f"**Run ID**: `{run_id}`  \n")
            f.write(f"**Gym Version**: `{gym_version}`\n\n")
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
    gym_version: str = "unknown",
):
    """
    Save a detailed trajectory JSON for this model run.

    Structure:
        trajectories/<gym>/<run_id>/<model_name>.json

    The JSON contains:
      - run metadata (run_id, model, gym, gym_version, timestamp, temperature, reward_mode)
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
        "gym_version": gym_version,
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


# ── Model Worker (used by both sequential and parallel modes) ──

def _run_single_model(
    model: str,
    gym_name: str,
    gym_config: dict,
    base_url: str,
    api_url: str,
    scenarios: list,
    temperature: float,
    max_tokens: int,
    reward_mode: str,
    run_id: str,
    save: bool,
    trajectory: bool,
    verbose: bool,
    gym_version: str = "unknown",
) -> Dict[str, Any]:
    """
    Run all scenarios for a single model.

    This function is self-contained: it creates its own env_client, runner,
    and checker. This makes it safe to call from multiple threads for
    parallel evaluation — each thread has fully isolated resources.

    For API-based gyms (like inventory), the OpenEnv environment creates
    session-scoped isolated databases, so multiple models can run
    simultaneously against the same Docker container without interference.

    Returns:
        Dict with model name, per-scenario results, and timing info.
    """
    model_start = time.time()
    model_results = []

    # Each worker gets its own AutoEnv client (→ own WebSocket → own environment instance)
    env_client = AutoEnv.from_env(gym_name, base_url=base_url)
    env_client.__enter__()

    # Each worker gets its own checker (session_id set dynamically by the runner)
    checker = gym_config["checker_factory"](api_url)

    # Each worker gets its own transform
    transform = None
    if reward_mode == "openenv":
        transform = gym_config["transform_factory"]()

    # Create agent runner
    runner = AgentRunner(
        model=model,
        env_client=env_client,
        temperature=temperature,
        max_tokens=max_tokens,
        reward_mode=reward_mode,
        transform=transform,
    )

    try:
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n  [{model}] Scenario {i}/{len(scenarios)}: {scenario.id}")

            start = time.time()
            try:
                episode, breakdown = runner.run_scenario(scenario, checker)
                elapsed = time.time() - start

                # Outcome checks (checker is already session-scoped from runner)
                outcome_results = checker.check_all(scenario.outcome_checks)

                model_results.append({
                    "scenario": scenario.id,
                    "total_reward": breakdown.total,
                    "breakdown": breakdown,
                    "steps": len(episode.steps),
                    "elapsed": elapsed,
                    "episode": episode,
                    "outcome_results": outcome_results,
                })

                print(f"  [{model}] {scenario.id}: {breakdown.total:.2f} ({len(episode.steps)} steps, {elapsed:.1f}s)")

            except Exception as e:
                elapsed = time.time() - start
                logger.exception(f"[{model}] Scenario {scenario.id} failed")
                model_results.append({
                    "scenario": scenario.id,
                    "total_reward": 0.0,
                    "breakdown": None,
                    "steps": 0,
                    "elapsed": elapsed,
                    "error": str(e),
                })
                print(f"  [{model}] {scenario.id}: ERROR — {e}")

    finally:
        if hasattr(checker, "close"):
            checker.close()
        env_client.__exit__(None, None, None)

    model_elapsed = time.time() - model_start

    # Save results and trajectory for this model
    if save:
        output_path = os.path.join(
            os.path.dirname(__file__), "results", gym_name, f"{run_id}.md"
        )
        save_results_to_markdown(
            results=model_results,
            model=model,
            gym=gym_name,
            output_path=output_path,
            total_elapsed=model_elapsed,
            temperature=temperature,
            run_id=run_id,
            reward_mode=reward_mode,
            gym_version=gym_version,
        )

    if trajectory:
        save_trajectory(
            results=model_results,
            scenarios=scenarios,
            model=model,
            gym=gym_name,
            temperature=temperature,
            total_elapsed=model_elapsed,
            run_id=run_id,
            reward_mode=reward_mode,
            gym_version=gym_version,
        )

    return {
        "model": model,
        "results": model_results,
        "elapsed": model_elapsed,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate an LLM agent against OpenEnv gym scenarios.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prerequisites:
  pip install -e inventory/          # install gym for AutoEnv discovery
  pip install -e browser/            # install browser gym

Examples:
  # Inventory gym
  python run_eval.py --gym inventory --model gpt-4o
  python run_eval.py --gym inventory --model gpt-4o --reward-mode openenv

  # Browser gym (Node.js + React e-commerce app)
  python run_eval.py --gym browser --model gpt-5.4 --save --trajectory
  python run_eval.py --gym browser --model gpt-5.4,claude-sonnet-4-6,claude-opus-4-6 --parallel 3

  # Parallel (multiple models)
  python run_eval.py --gym inventory --model gpt-4o-mini,gpt-4o,claude-sonnet-4-6 --parallel 3
  python run_eval.py --gym inventory --model gpt-4o-mini,gpt-4o --parallel 2 --save --trajectory

  # Other options
  python run_eval.py --gym inventory --model gpt-4o --scenario create_product
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
        help="LiteLLM model string, or comma-separated for parallel mode "
             "(e.g., 'gpt-4o' or 'gpt-4o-mini,gpt-4o,claude-sonnet-4-6')",
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help="Run a specific scenario by ID (default: run all)",
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
        help="Save results to results/<gym>/<run_id>.md",
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
        "--parallel",
        type=int,
        default=1,
        help="Number of models to evaluate in parallel (default: 1 = sequential). "
             "Use with comma-separated --model values. Each model gets its own "
             "isolated DB session via OpenEnv concurrent sessions.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Parse model list (comma-separated for parallel)
    models = [m.strip() for m in args.model.split(",") if m.strip()]

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
    base_url = _resolve_base_url(args.gym)  # auto-derived from openenv.yaml port
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

    # AutoEnv discovery (verify once — individual workers create their own clients)
    divider("AutoEnv Discovery")
    print(f"  Discovering gym '{args.gym}' via AutoEnv...")
    env_info = AutoEnv.get_env_info(args.gym)
    print(f"  Found: {env_info['name']} (package: {env_info['package']}, v{env_info['version']})")
    print(f"  Client class: {env_info['env_class']} from {env_info['module']}")
    print(f"  Base URL: {base_url} (auto-derived from openenv.yaml port)")

    # Fetch EnvironmentMetadata from the running OpenEnv server
    gym_metadata = _fetch_gym_metadata(base_url)
    if gym_metadata:
        print(f"\n  ── Environment Metadata (GET {base_url}/metadata) ──")
        print(f"  Name:        {gym_metadata.get('name', 'N/A')}")
        print(f"  Version:     {gym_metadata.get('version', 'N/A')}")
        print(f"  Description: {gym_metadata.get('description', 'N/A')}")
        print(f"  Author:      {gym_metadata.get('author', 'N/A')}")
        if gym_metadata.get("documentation_url"):
            print(f"  Docs:        {gym_metadata['documentation_url']}")
    else:
        print(f"\n  ⚠ Could not fetch /metadata from {base_url} (server may not be running)")

    # Determine execution mode
    is_parallel = args.parallel > 1 and len(models) > 1
    mode_str = f"Parallel ({args.parallel} workers)" if is_parallel else "Sequential"

    # Extract gym version from metadata (if available)
    gym_version = gym_metadata.get("version", "unknown") if gym_metadata else "unknown"

    # Print header
    divider("LLM Evaluation Run")
    print(f"  Gym:          {args.gym} (v{gym_version})")
    print(f"  Models:       {', '.join(models)}")
    print(f"  Run ID:       {run_id}")
    print(f"  Mode:         {mode_str}")
    print(f"  Discovery:    AutoEnv ({env_info['package']})")
    print(f"  Base URL:     {base_url}")
    print(f"  API URL:      {api_url}")
    print(f"  Scenarios:    {len(scenarios)} of {len(all_scenarios)}")
    print(f"  Temperature:  {args.temperature}")
    print(f"  Reward Mode:  {args.reward_mode}")

    if is_parallel:
        print(f"\n  Concurrent sessions: Each model gets an isolated DB via OpenEnv sessions.")

    # ── Execute ──
    total_start = time.time()
    all_model_results = []

    if is_parallel:
        # ── Parallel Mode ──
        # Each model runs in its own thread with isolated resources:
        # - Own AutoEnv client (own WebSocket → own InventoryEnvironment instance)
        # - Own session-scoped database (via X-Session-ID)
        # - Own checker (routed to session DB)
        divider(f"Parallel Evaluation ({len(models)} models, {args.parallel} workers)")

        max_workers = min(args.parallel, len(models))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for model in models:
                future = executor.submit(
                    _run_single_model,
                    model=model,
                    gym_name=args.gym,
                    gym_config=gym_config,
                    base_url=base_url,
                    api_url=api_url,
                    scenarios=scenarios,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    reward_mode=args.reward_mode,
                    run_id=run_id,
                    save=args.save,
                    trajectory=args.trajectory,
                    verbose=args.verbose,
                    gym_version=gym_version,
                )
                futures[future] = model

            for future in as_completed(futures):
                model = futures[future]
                try:
                    result = future.result()
                    all_model_results.append(result)
                    print(f"\n  ✅ {model} completed in {result['elapsed']:.1f}s")
                except Exception as e:
                    print(f"\n  ❌ {model} FAILED: {e}")
                    logger.exception(f"Model {model} failed")
                    all_model_results.append({
                        "model": model,
                        "results": [],
                        "elapsed": 0.0,
                        "error": str(e),
                    })

    else:
        # ── Sequential Mode (backward compatible) ──
        for model in models:
            if len(models) > 1:
                divider(f"Model: {model}")

            # For single-model sequential, show the detailed output
            if len(models) == 1:
                # Use the existing detailed flow for single model
                result = _run_single_model_detailed(
                    model=model,
                    gym_name=args.gym,
                    gym_config=gym_config,
                    base_url=base_url,
                    api_url=api_url,
                    scenarios=scenarios,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    reward_mode=args.reward_mode,
                    run_id=run_id,
                    save=args.save,
                    trajectory=args.trajectory,
                    gym_version=gym_version,
                )
            else:
                result = _run_single_model(
                    model=model,
                    gym_name=args.gym,
                    gym_config=gym_config,
                    base_url=base_url,
                    api_url=api_url,
                    scenarios=scenarios,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    reward_mode=args.reward_mode,
                    run_id=run_id,
                    save=args.save,
                    trajectory=args.trajectory,
                    verbose=args.verbose,
                    gym_version=gym_version,
                )
            all_model_results.append(result)

    # ── Print Overall Summary ──
    total_elapsed = time.time() - total_start
    divider("Evaluation Summary")

    for mr in all_model_results:
        model = mr["model"]
        results = mr.get("results", [])
        model_elapsed = mr.get("elapsed", 0.0)

        if not results:
            print(f"\n  Model: {model} — FAILED ({mr.get('error', 'unknown')})")
            continue

        total_reward = sum(r["total_reward"] for r in results)
        avg_reward = total_reward / len(results) if results else 0.0

        print(f"\n  Model: {model}")
        print(f"  Time:  {model_elapsed:.1f}s")
        print(f"  {'Scenario':<30} {'Reward':>8} {'Steps':>6} {'Time':>6}")
        print(f"  {'─' * 30} {'─' * 8} {'─' * 6} {'─' * 6}")

        for r in results:
            reward_str = f"{r['total_reward']:.2f}" if r.get("breakdown") else "ERROR"
            print(f"  {r['scenario']:<30} {reward_str:>8} {r['steps']:>6} {r['elapsed']:>5.1f}s")

        print(f"  {'─' * 30} {'─' * 8} {'─' * 6} {'─' * 6}")
        print(f"  {'AVERAGE':<30} {avg_reward:>8.2f}")

    # Overall timing
    if len(models) > 1:
        print(f"\n  Total time (all models): {total_elapsed:.1f}s")
        if is_parallel:
            seq_time = sum(mr.get("elapsed", 0.0) for mr in all_model_results)
            speedup = seq_time / total_elapsed if total_elapsed > 0 else 1.0
            print(f"  Sequential equivalent:   {seq_time:.1f}s")
            print(f"  Speedup:                 {speedup:.1f}x")


def _run_single_model_detailed(
    model: str,
    gym_name: str,
    gym_config: dict,
    base_url: str,
    api_url: str,
    scenarios: list,
    temperature: float,
    max_tokens: int,
    reward_mode: str,
    run_id: str,
    save: bool,
    trajectory: bool,
    gym_version: str = "unknown",
) -> Dict[str, Any]:
    """
    Run all scenarios for a single model with DETAILED per-step output.

    This preserves the existing detailed output format for the common case
    of running a single model (backward compatible).
    """
    model_start = time.time()
    results = []

    env_client = AutoEnv.from_env(gym_name, base_url=base_url)
    env_client.__enter__()

    checker = gym_config["checker_factory"](api_url)

    transform = None
    if reward_mode == "openenv":
        transform = gym_config["transform_factory"]()

    runner = AgentRunner(
        model=model,
        env_client=env_client,
        temperature=temperature,
        max_tokens=max_tokens,
        reward_mode=reward_mode,
        transform=transform,
    )

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
        if hasattr(checker, "close"):
            checker.close()
        env_client.__exit__(None, None, None)
        logger.info("AutoEnv client disconnected.")

    model_elapsed = time.time() - model_start

    # Save
    if save:
        output_path = os.path.join(
            os.path.dirname(__file__), "results", gym_name, f"{run_id}.md"
        )
        save_results_to_markdown(
            results=results,
            model=model,
            gym=gym_name,
            output_path=output_path,
            total_elapsed=model_elapsed,
            temperature=temperature,
            run_id=run_id,
            reward_mode=reward_mode,
            gym_version=gym_version,
        )
        print(f"\n  Results saved: {output_path}")

    if trajectory:
        save_trajectory(
            results=results,
            scenarios=scenarios,
            model=model,
            gym=gym_name,
            temperature=temperature,
            total_elapsed=model_elapsed,
            run_id=run_id,
            reward_mode=reward_mode,
            gym_version=gym_version,
        )

    return {
        "model": model,
        "results": results,
        "elapsed": model_elapsed,
    }


def _short_json(obj, max_len=80):
    """Compact JSON string, truncated if too long."""
    s = json.dumps(obj, default=str)
    return s if len(s) <= max_len else s[:max_len] + "..."


if __name__ == "__main__":
    main()
