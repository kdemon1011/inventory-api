# Docker Deployment

Docker is core to OpenEnv — isolated, reproducible environments that run identically everywhere.

## Why Docker

- **Isolation**: Each gym runs in its own container with its own dependencies
- **Reproducibility**: Same image → same behavior on any machine
- **One command**: `docker run -p 9000:9000 openenv-inventory` — everything is running
- **Security**: The LLM agent interacts only through OpenEnv's API, not directly with the system

## Architecture Patterns

### Single-Process (simple gyms)

For gyms that store data in-memory or don't need a separate backend:

```
┌─────────────── Docker Container ───────────────┐
│                                                 │
│   OpenEnv Server (MCPEnvironment) → port 9000   │
│   In-memory data store                          │
│                                                 │
└─────────────────────────────────────────────────┘
```

Example: `inventory_clone/`

Dockerfile CMD:
```dockerfile
CMD ["sh", "-c", "cd /app/env && uvicorn server.app:app --host 0.0.0.0 --port 9000"]
```

### Two-Process (real backend gyms)

For gyms that wrap a real API with a database:

```
┌────────────────────── Docker Container ─────────────────────┐
│                                                              │
│   Process 1: Backend API (FastAPI + SQLite)  → port 8000     │
│   Process 2: OpenEnv Server (MCPEnvironment) → port 9000     │
│                                                              │
│   Startup: API starts first, health-checked, then OpenEnv    │
└──────────────────────────────────────────────────────────────┘
```

Example: `inventory/`

Dockerfile CMD (startup logic inlined):
```dockerfile
CMD ["bash", "-c", "cd /app/env && python main.py & \
    echo 'Waiting for API...' && \
    for i in $(seq 1 30); do \
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
            echo 'API is ready.' && break; \
        fi; \
        if [ \"$i\" -eq 30 ]; then echo 'ERROR: API failed to start.' && exit 1; fi; \
        sleep 1; \
    done && \
    echo 'Starting OpenEnv server on port 9000...' && \
    exec uvicorn server.app:app --host 0.0.0.0 --port 9000"]
```

## Building

### From the gym directory

```bash
cd inventory
docker build -t openenv-inventory -f Dockerfile .
```

### Using `openenv build` (if available)

```bash
openenv build inventory/
```

## Running

```bash
# Single-process gym
docker run -d --name inventory_clone -p 9000:9000 openenv-inventory-clone

# Two-process gym (expose both ports)
docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory

# Verify
curl http://localhost:9000/health
```

## Evaluating Against Docker

```bash
# Start the gym
docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory

# Run a single model evaluation
python run_eval.py --gym inventory --model gpt-4o --save --trajectory

# Run multiple models in parallel (concurrent sessions)
python run_eval.py --gym inventory \
  --model gpt-4o-mini,gpt-4o,claude-sonnet-4-6 \
  --parallel 3 \
  --save --trajectory

# Stop
docker stop inventory && docker rm inventory
```

### Concurrent Sessions

A single Docker container supports **multiple concurrent evaluations**. When using `--parallel N`:

- Each model gets its own `InventoryEnvironment` instance via a separate WebSocket connection
- Each instance creates an isolated SQLite database in `data/sessions/<uuid>.db` inside the container
- All HTTP requests include `X-Session-ID` header for database routing
- Session databases are automatically cleaned up when the evaluation finishes

No extra containers or port mappings needed — one container handles it all.

## Dockerfile Structure

All gym Dockerfiles follow the same multi-stage pattern:

```dockerfile
# Stage 1: Builder — install dependencies
ARG BASE_IMAGE=ghcr.io/meta-pytorch/openenv-base:latest
FROM ${BASE_IMAGE} AS builder
WORKDIR /app
COPY . /app/env
WORKDIR /app/env
RUN uv sync --frozen --no-editable

# Stage 2: Runtime — copy only what's needed
FROM ${BASE_IMAGE}
COPY --from=builder /app/env/.venv /app/.venv
COPY --from=builder /app/env /app/env
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/env:$PYTHONPATH"
EXPOSE 9000
CMD [...]
```

- **Builder stage**: Installs all dependencies using `uv sync` with caching
- **Runtime stage**: Copies the virtual environment and source code, sets up PATH
- **PYTHONPATH**: Set to `/app/env` so imports work correctly from the gym root
- **Health check**: Container reports healthy when the OpenEnv server responds

## Note on Local Development

Docker is the only supported execution method. All gyms are designed to run as Docker containers — this ensures isolation, reproducibility, and a clean database on each restart. Manual server starts (`python main.py`, `uv run server`) are not recommended and are not tested as part of the evaluation pipeline.
