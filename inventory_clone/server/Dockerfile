# Inventory Clone — Single-process OpenEnv Docker image
#
# Unlike the full Inventory gym (which runs a separate backend API on port 8000),
# this clone uses in-memory storage, so only one process is needed.
#
# Build:  docker build -t openenv-inventory-clone -f server/Dockerfile ..
#         (from inventory_clone/ directory)
#   OR:   openenv build inventory_clone/
#
# Run:    docker run -p 9000:9000 openenv-inventory-clone

ARG BASE_IMAGE=ghcr.io/meta-pytorch/openenv-base:latest
FROM ${BASE_IMAGE} AS builder

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

ARG BUILD_MODE=standalone
ARG ENV_NAME=inventory_clone

COPY . /app/env

WORKDIR /app/env

RUN if ! command -v uv >/dev/null 2>&1; then \
        curl -LsSf https://astral.sh/uv/install.sh | sh && \
        mv /root/.local/bin/uv /usr/local/bin/uv && \
        mv /root/.local/bin/uvx /usr/local/bin/uvx; \
    fi

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

COPY --from=builder /app/env/.venv /app/.venv
COPY --from=builder /app/env /app/env

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/env:$PYTHONPATH"

EXPOSE 9001

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9001/health || exit 1

# Single process — just the OpenEnv server (in-memory storage, no backend API)
CMD ["sh", "-c", "cd /app/env && uvicorn server.app:app --host 0.0.0.0 --port 9001"]
