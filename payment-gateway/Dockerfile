# Payment Gateway Gym — Docker image for OpenEnv deployment
#
# Single container running 3 services:
#   1. Stripe Mock  (Node.js, port 3001) — starts first
#   2. Payment Gateway API (Python, port 8002) — starts after Stripe mock is healthy
#   3. OpenEnv Server (Python, port 9002) — starts after Gateway API is healthy
#
# Build:
#   cd payment-gateway && docker build -t openenv-payment-gateway .
#
# Run:
#   docker run -d --name payment-gateway -p 8002:8002 -p 9002:9002 openenv-payment-gateway
#
# Run with more concurrent sessions (default: 4):
#   docker run -d -p 8002:8002 -p 9002:9002 -e MAX_CONCURRENT_ENVS=8 openenv-payment-gateway

ARG BASE_IMAGE=ghcr.io/meta-pytorch/openenv-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /app

# Install Node.js (for the Stripe mock) and build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl nodejs npm && \
    rm -rf /var/lib/apt/lists/*

# Build Stripe mock dependencies (copied separately, excluded from Python COPY via .dockerignore)
COPY stripe-mock/ /app/stripe-mock/
RUN cd /app/stripe-mock && npm install --production

# Copy Python project (.dockerignore excludes stripe-mock/node_modules, __pycache__, .venv, data/)
COPY . /app/env
WORKDIR /app/env

# Ensure uv is available
RUN if ! command -v uv >/dev/null 2>&1; then \
        curl -LsSf https://astral.sh/uv/install.sh | sh && \
        mv /root/.local/bin/uv /usr/local/bin/uv && \
        mv /root/.local/bin/uvx /usr/local/bin/uvx; \
    fi

# Install Python dependencies (two-phase for caching)
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

# Install Node.js runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy from builder
COPY --from=builder /app/env/.venv /app/.venv
COPY --from=builder /app/env /app/env
COPY --from=builder /app/stripe-mock /app/stripe-mock

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/env:$PYTHONPATH"

# Expose ports: OpenEnv (9002) + Gateway API (8002). Stripe mock (3001) is internal only.
EXPOSE 8002 9002

# Health check against the OpenEnv server
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:9002/health || exit 1

# Create data directories for session-scoped SQLite DBs
RUN mkdir -p /app/env/data/sessions

# Start all 3 services with health-check gating between each:
#   1. Stripe mock  → wait for :3001/health
#   2. Gateway API  → wait for :8002/health
#   3. OpenEnv      → foreground (exec)
CMD ["bash", "-c", "\
  cd /app/stripe-mock && node index.js & \
  for i in $(seq 1 30); do curl -sf http://localhost:3001/health >/dev/null 2>&1 && echo 'Stripe mock ready' && break; sleep 1; done; \
  cd /app/env && python main.py & \
  for i in $(seq 1 30); do curl -sf http://localhost:8002/health >/dev/null 2>&1 && echo 'Gateway API ready' && break; sleep 1; done; \
  exec uvicorn server.app:app --host 0.0.0.0 --port 9002"]
