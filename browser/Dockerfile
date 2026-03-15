# Browser Gym — Docker image for OpenEnv deployment
#
# Runs two services in a single container:
#   1. Node.js Express web app (port 8003) — serves API + React SPA
#   2. Python OpenEnv server (port 9003)  — MCP tools for agent interaction
#
# Build:
#   cd browser && docker build -t openenv-browser .
#
# Run:
#   docker run -d --name browser -p 8003:8003 -p 9003:9003 openenv-browser
#
# Override concurrency:
#   docker run -d --name browser -p 8003:8003 -p 9003:9003 -e MAX_CONCURRENT_ENVS=8 openenv-browser

ARG BASE_IMAGE=ghcr.io/meta-pytorch/openenv-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /app

# Install Node.js 22.x, npm, git, curl, build tools for native modules
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git curl ca-certificates gnupg \
        python3 make g++ && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# ── Stage 1a: Build Node.js webapp ──

COPY webapp/ /app/webapp/
RUN cd /app/webapp && \
    npm ci 2>/dev/null || npm install && \
    npm run build && \
    rm -rf node_modules && \
    npm ci --omit=dev 2>/dev/null || npm install --omit=dev

# ── Stage 1b: Build Python environment ──

COPY . /app/env
RUN rm -rf /app/env/webapp
WORKDIR /app/env

# Ensure uv is available
RUN if ! command -v uv >/dev/null 2>&1; then \
        curl -LsSf https://astral.sh/uv/install.sh | sh && \
        mv /root/.local/bin/uv /usr/local/bin/uv && \
        mv /root/.local/bin/uvx /usr/local/bin/uvx; \
    fi

# Install Python deps (two-phase for cache efficiency)
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

# ── Stage 2: Runtime ──

FROM ${BASE_IMAGE}

WORKDIR /app

# Install Node.js runtime only (no build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy built webapp (includes node_modules + dist/)
COPY --from=builder /app/webapp /app/webapp

# Copy Python venv and project
COPY --from=builder /app/env/.venv /app/.venv
COPY --from=builder /app/env /app/env

# Set PATH and PYTHONPATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/env:$PYTHONPATH"

# Expose both ports
EXPOSE 8003 9003

# Health check against the OpenEnv server
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:9003/health || exit 1

# Create session data directory
RUN mkdir -p /app/webapp/data/sessions

# Start Express webapp, wait for health, then start OpenEnv server
CMD ["bash", "-c", "\
  cd /app/webapp && node server.js & \
  for i in $(seq 1 30); do \
    curl -sf http://localhost:8003/health >/dev/null 2>&1 && echo 'Web app ready' && break; \
    sleep 1; \
  done; \
  cd /app/env && exec uvicorn server.app:app --host 0.0.0.0 --port 9003"]
