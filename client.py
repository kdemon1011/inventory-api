"""
Client for the Inventory OpenEnv Environment.

This is what YOU (or an RL framework, or a test script) uses to interact
with the Inventory OpenEnv environment.

Instead of manually making HTTP requests, you just do:
    client = InventoryEnvClient("http://localhost:9000")
    client.reset()
    client.step("create_product", {"name": "Mouse", "sku": "M1", "price": 9.99})
    client.state()

Two modes available:
  1. Sync (simple, for testing):     InventoryEnvClient
  2. Async (recommended, for RL):    AsyncInventoryEnvClient

Example (sync):
    with InventoryEnvClient("http://localhost:9000") as client:
        result = client.reset()
        print(result["observation"]["data"]["task"])
        
        result = client.step("create_product", {"name": "Mouse", "sku": "M1", "price": 9.99})
        print(f"Reward: {result['reward']}")
"""

import httpx


class InventoryEnvClient:
    """
    Synchronous client for the Inventory OpenEnv environment.
    
    Use this for testing and simple scripts.
    Supports 'with' statement for automatic cleanup.
    """

    def __init__(self, base_url: str = "http://localhost:9000"):
        """
        Args:
            base_url: URL of the OpenEnv server (NOT the Inventory API directly).
                      The OpenEnv server runs on port 9000 by default.
        """
        self.base_url = base_url
        self.http = httpx.Client(base_url=base_url, timeout=30.0)

    def reset(self, task_index: int = 0) -> dict:
        """
        Start a new episode.
        
        Args:
            task_index: Which task to give the agent (0, 1, or 2)
            
        Returns:
            dict with:
              - observation: Initial observation (task description + available tools)
              - state: Fresh episode state
        """
        response = self.http.post("/reset", json={"task_index": task_index})
        response.raise_for_status()
        return response.json()

    def step(self, tool: str, parameters: dict = None) -> dict:
        """
        Take one action in the environment.
        
        Args:
            tool: Which API tool to call (e.g., "create_product", "list_products")
            parameters: Parameters for the tool (e.g., {"name": "Mouse", "sku": "M1"})
            
        Returns:
            dict with:
              - observation: What happened (success/failure + data)
              - reward: Score for this action
              - done: Whether the episode is finished
              - state: Updated episode state
        """
        response = self.http.post("/step", json={
            "tool": tool,
            "parameters": parameters or {},
        })
        response.raise_for_status()
        return response.json()

    def state(self) -> dict:
        """
        Get the current episode state.
        
        Returns:
            dict with:
              - state: Current episode tracking info
              - action_history: All actions taken so far
        """
        response = self.http.get("/state")
        response.raise_for_status()
        return response.json()

    def health(self) -> dict:
        """Check if the OpenEnv server is healthy."""
        response = self.http.get("/health")
        response.raise_for_status()
        return response.json()

    def close(self):
        """Close the HTTP client."""
        self.http.close()

    # Support 'with' statement
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AsyncInventoryEnvClient:
    """
    Async client for the Inventory OpenEnv environment.
    
    Use this for RL training and high-performance scenarios.
    Supports 'async with' statement for automatic cleanup.
    
    Example:
        async with AsyncInventoryEnvClient("http://localhost:9000") as client:
            result = await client.reset()
            result = await client.step("create_product", {...})
    """

    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url
        self.http = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def reset(self, task_index: int = 0) -> dict:
        """Start a new episode."""
        response = await self.http.post("/reset", json={"task_index": task_index})
        response.raise_for_status()
        return response.json()

    async def step(self, tool: str, parameters: dict = None) -> dict:
        """Take one action in the environment."""
        response = await self.http.post("/step", json={
            "tool": tool,
            "parameters": parameters or {},
        })
        response.raise_for_status()
        return response.json()

    async def state(self) -> dict:
        """Get current episode state."""
        response = await self.http.get("/state")
        response.raise_for_status()
        return response.json()

    async def health(self) -> dict:
        """Health check."""
        response = await self.http.get("/health")
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        await self.http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
