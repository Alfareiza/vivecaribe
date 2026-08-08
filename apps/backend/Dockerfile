# syntax=docker/dockerfile:1
# Portable API image (Compose / AWS / any OCI runtime). Build from this directory:
#   docker build -t vivecaribe-api .
# Or via Compose: context ./apps/backend

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    APP_DATA_DIR=/data

WORKDIR /app

RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --home /app --shell /usr/sbin/nologin app \
    && mkdir -p /data \
    && chown -R app:app /data

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY booking_providers.yaml ./booking_providers.yaml

# Python package ≠ browser binaries. Install Chromium + OS libs as root,
# then hand ownership to the non-root runtime user.
RUN playwright install --with-deps chromium \
    && chown -R app:app /ms-playwright

USER app

EXPOSE 8000

CMD ["uvicorn", "vivecaribe.main:app", "--host", "0.0.0.0", "--port", "8000"]
