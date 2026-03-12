# Creating a New Gym

This guide walks through creating a new gym from scratch using `openenv init`, customizing it, and registering it for evaluation.

## Scaffolding

```bash
openenv init my_new_gym
```

This generates a complete environment template with all required files. The default template uses the **Gymnasium-style** pattern (typed Action/Observation classes). If your gym wraps an API with multiple operations, you'll want to convert it to the **MCP-tool pattern**.

## What Gets Generated

```
my_new_gym/
├── __init__.py                         # Package exports
├── client.py                           # EnvClient (typed) — convert to MCPToolClient for MCP
├── models.py                           # Action/Observation models — remove for MCP pattern
├── openenv.yaml                        # Environment manifest
├── pyproject.toml                      # Dependencies & entry points
├── README.md                           # Documentation
├── uv.lock                             # Lock file (auto-generated)
└── server/
    ├── __init__.py
    ├── app.py                          # create_app() wiring
    ├── my_new_gym_environment.py       # Environment class
    ├── Dockerfile                      # Docker build
    └── requirements.txt                # Remove (use pyproject.toml)
```

## Choosing a Pattern

| Aspect | Gymnasium-Style | MCP-Tool-Style |
|--------|----------------|----------------|
| Base class | `Environment` | `MCPEnvironment` |
| Actions | Typed (`MyAction`) | Dynamic (`CallToolAction`) |
| Client | `EnvClient[Action, Obs]` | `MCPToolClient` |
| Agent discovers tools via | Fixed schema | `list_tools()` at runtime |
| Best for | Simple envs, game moves | Complex APIs, multiple operations |
| Example | Chess, Tic-tac-toe | Inventory, Browser, E-commerce |

**If your gym wraps an API or has more than 2-3 operations, use MCP-tool pattern.**

## Customizing for MCP-Tool Pattern

### Environment class (`server/my_new_gym_environment.py`)

Convert from `Environment` to `MCPEnvironment`:

```python
# BEFORE (Gymnasium-style template)
from openenv.core.env_server.interfaces import Environment

class MyNewGymEnvironment(Environment):
    def step(self, action: MyAction) -> MyObservation:
        return MyObservation(echoed_message=action.message)
```

```python
# AFTER (MCP-tool pattern)
from openenv.core.env_server.mcp_environment import MCPEnvironment
from fastmcp import FastMCP

class MyNewGymEnvironment(MCPEnvironment):
    def __init__(self):
        mcp = FastMCP("my_new_gym")

        @mcp.tool()
        def do_something(param: str) -> dict:
            """Tool description — the agent sees this."""
            return {"result": "done"}

        super().__init__(mcp)  # KEY LINE — registers all tools

    def reset(self, seed=None, episode_id=None, **kwargs):
        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        return Observation(done=False, reward=0.0, metadata={"status": "ready"})

    def step(self, action, timeout_s=None, **kwargs):
        self._state.step_count += 1
        return super().step(action, timeout_s=timeout_s, **kwargs)

    @property
    def state(self):
        return self._state
```

### Server app (`server/app.py`)

Add the MCP discriminated union so both `ListToolsAction` and `CallToolAction` are handled:

```python
from typing import Any, Union
from pydantic import TypeAdapter
from openenv.core.env_server.http_server import create_app
from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation, ListToolsAction
from openenv.core.env_server.types import Action

_mcp_action_adapter = TypeAdapter(Union[ListToolsAction, CallToolAction])

class MCPAction(Action):
    @classmethod
    def model_validate(cls, data: Any, **kwargs: Any) -> Action:
        return _mcp_action_adapter.validate_python(data)

app = create_app(
    MyNewGymEnvironment, MCPAction, CallToolObservation,
    env_name="my_new_gym",
)

def main(host="0.0.0.0", port=9000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
```

### Client (`client.py`)

Replace the typed `EnvClient` with `MCPToolClient` and add **Action/Observation aliases** for AutoEnv discovery:

```python
from openenv.core.mcp_client import MCPToolClient
from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation

class MyNewGymEnv(MCPToolClient):
    """Client for MyNewGym — discoverable via AutoEnv.from_env('my_new_gym')."""
    pass

# Type aliases for AutoEnv / AutoAction auto-discovery
MyNewGymAction = CallToolAction
MyNewGymObservation = CallToolObservation
```

These aliases are required for `AutoEnv.from_env()` and `AutoAction.from_env()` to work.

### Clean up

- Delete `models.py` (MCP-tool pattern doesn't use typed Action/Observation)
- Delete `server/requirements.txt` (dependencies are in `pyproject.toml`)
- Update `__init__.py` to export only the client

### Update dependencies (`pyproject.toml`)

Add `fastmcp` for the MCP-tool pattern and configure the package for pip-installability:

```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "openenv-my-new-gym"
version = "0.1.0"
description = "My New Gym — a brief description"
requires-python = ">=3.10"
dependencies = [
    "openenv-core[core]>=0.2.0",
    "fastmcp>=0.2.0",
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "pydantic>=2.5.0",
    # Add your gym-specific dependencies here
]

[project.scripts]
server = "my_new_gym.server.app:main"

[tool.setuptools]
include-package-data = true
packages = ["my_new_gym", "my_new_gym.server"]
package-dir = {"my_new_gym" = ".", "my_new_gym.server" = "server"}

# IMPORTANT: Include openenv.yaml so AutoEnv can discover the gym
[tool.setuptools.package-data]
my_new_gym = ["openenv.yaml"]
```

Then regenerate the lock file:

```bash
cd my_new_gym && uv lock
```

### Make it pip-installable (required for AutoEnv)

AutoEnv discovers gyms from pip-installed packages. Install in editable mode:

```bash
pip install -e my_new_gym/
```

Verify discovery:

```bash
python -c "from openenv import AutoEnv; AutoEnv.list_environments()"
```

You should see your gym listed with its name, description, and version.

> **Why editable mode?** `pip install -e` creates a link to your source code so changes are reflected immediately without reinstalling. This is essential during development.

### Update port in `openenv.yaml`

Each gym runs its own OpenEnv server on its own port. Pick a unique port that doesn't conflict with other gyms:

| Gym | OpenEnv Port | Backend API Port |
|-----|-------------|-----------------|
| `inventory` | 9000 | 8000 |
| `inventory_clone` | 9001 | — (in-memory) |
| `my_new_gym` | 9002 | 8002 (if needed) |

```yaml
spec_version: 1
name: my_new_gym
type: space
runtime: fastapi
app: server.app:app
port: 9002
```

## Validation

```bash
openenv validate my_new_gym/
# Expected: [OK] my_new_gym: Ready for multi-mode deployment
```

## Running Locally

```bash
cd my_new_gym
uv sync        # install dependencies
uv run server  # start on port 9000
```

Test:
```bash
curl http://localhost:9000/health
```

## Adding Scenarios

Create `scenarios/my_new_gym.py`:

```python
from rewards.base import Scenario

MY_GYM_SCENARIOS = [
    Scenario(
        id="basic_task",
        prompt="Do something specific with the tools available.",
        expected_tools=["do_something"],
        outcome_checks=[
            {"type": "exists", "field": "result", "value": "done"},
        ],
        max_steps=5,
    ),
]
```

## Adding Reward Checker

Create `rewards/my_new_gym_checks.py`:

```python
class MyNewGymChecker:
    def __init__(self, api_url=None):
        # connect to your backend if needed
        pass

    def check_all(self, checks):
        results = []
        for check in checks:
            # verify ground truth
            results.append(True)  # or False
        return results

    def close(self):
        pass
```

## Adding Transform (for OpenEnv reward mode)

Create `rewards/transforms/my_new_gym.py`:

```python
from .base import StepRewardTransform
from openenv.core.env_server.mcp_types import CallToolObservation
from openenv.core.env_server.types import Observation

class MyNewGymStepTransform(StepRewardTransform):
    def _compute_reward(self, observation: Observation) -> float:
        if not isinstance(observation, CallToolObservation):
            return 0.0
        if observation.error is not None:
            return -0.5
        # Score based on result quality (gym-specific logic)
        return 1.0
```

## Registering in `run_eval.py`

Add to `GYM_REGISTRY`:

```python
GYM_REGISTRY = {
    "inventory": { ... },
    "my_new_gym": {
        "scenarios_loader": lambda: _load_my_new_gym_scenarios(),
        "checker_factory": lambda api_url: _create_my_new_gym_checker(api_url),
        "transform_factory": lambda: _create_my_new_gym_transform(),
        "default_api_url": "http://localhost:8002",  # or None if in-memory
    },
}
```

`run_eval.py` uses `AutoEnv.from_env(gym_name, base_url=...)` where the base_url is **auto-derived** from the gym's `openenv.yaml` port. No hardcoded OpenEnv URLs needed — only the API URL for ground truth checking (which is NOT an OpenEnv concept).

## Checklist

- [ ] `openenv init my_new_gym`
- [ ] Customize environment (Gymnasium-style or MCP-tool)
- [ ] Update `server/app.py` (add MCPAction union if MCP-tool)
- [ ] Update `client.py` (MCPToolClient + Action/Observation aliases for AutoEnv)
- [ ] Update `pyproject.toml` (dependencies + package-data for `openenv.yaml`)
- [ ] `uv lock` to regenerate lock file
- [ ] `pip install -e my_new_gym/` to make it discoverable
- [ ] Verify: `python -c "from openenv import AutoEnv; AutoEnv.list_environments()"`
- [ ] `openenv validate my_new_gym/` — must pass
- [ ] Create scenarios: `scenarios/my_new_gym.py`
- [ ] Create reward checker: `rewards/my_new_gym_checks.py`
- [ ] Create transform: `rewards/transforms/my_new_gym.py`
- [ ] Register in `run_eval.py` → `GYM_REGISTRY`
- [ ] Test: `python run_eval.py --gym my_new_gym --model gpt-4o`

## Reference: `inventory_clone/`

The `inventory_clone/` folder is a working example of this exact process — scaffolded via `openenv init inventory_clone`, then customized for MCP-tool pattern with in-memory storage.
