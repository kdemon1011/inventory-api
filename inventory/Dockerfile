# Inventory Gym — Docker image for OpenEnv deployment
#
# Packages the Inventory API (port 8000) and OpenEnv server (port 9000)
# into a single container.
#
# Build:
#   openenv build inventory/
#   OR: cd inventory && docker build -t openenv-inventory .
#
# Run:
#   docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory
#
# The LLM agent connects to localhost:9000 (OpenEnv).
# The ground truth checker connects to localhost:8000 (API).

ARG BASE_IMAGE=ghcr.io/meta-pytorch/openenv-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /app

# Git required for installing VCS dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

ARG BUILD_MODE=standalone
ARG ENV_NAME=inventory

# Copy the entire gym into the container
COPY . /app/env

WORKDIR /app/env

# Ensure uv is available
RUN if ! command -v uv >/dev/null 2>&1; then \
        curl -LsSf https://astral.sh/uv/install.sh | sh && \
        mv /root/.local/bin/uv /usr/local/bin/uv && \
        mv /root/.local/bin/uvx /usr/local/bin/uvx; \
    fi

# Install dependencies using uv (two-phase: deps first, then project)
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f uv.lock ]; then \
        uv sync --frozen --no-install-project --no-editable; \
    else \
        uv sync --no-install-project --no-editable; \
    fi

RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -f uv.lock ]; then \
        uv sync --frozen --no-editable; \
    else \
        uv sync --no-editable; \
    fi

# ── Final runtime stage ──
FROM ${BASE_IMAGE}

WORKDIR /app

# Copy the virtual environment and project from builder
COPY --from=builder /app/env/.venv /app/.venv
COPY --from=builder /app/env /app/env

# Use the venv Python and add project to PYTHONPATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/env:$PYTHONPATH"

# Expose both ports: OpenEnv (9000) + Inventory API (8000)
EXPOSE 8000 9000

# Health check against the OpenEnv server
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Start Inventory API in background, wait for it, then start OpenEnv server
CMD ["bash", "-c", "cd /app/env && python main.py & for i in $(seq 1 30); do curl -sf http://localhost:8000/health >/dev/null 2>&1 && echo 'Inventory API ready' && break; sleep 1; done; exec uvicorn server.app:app --host 0.0.0.0 --port 9000"]
