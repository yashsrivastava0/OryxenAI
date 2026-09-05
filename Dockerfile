# Multi-stage Dockerfile for the OryxenAI application image.
# Serves the FastAPI API plus the compiled authenticated Preact product shell.

# ---- Stage 0: product frontend ----
FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

# Install from the lockfile before copying source so dependency layers remain
# cacheable while every image build produces the manifest-backed product bundle.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ---- Stage 1: builder ----
FROM python:3.13-slim-bookworm AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=3.13

# Install uv using the official standalone binary method.
COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

WORKDIR /app

# Copy only dependency manifests for cache-efficient install.
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment (no dev deps, no project).
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source (config/migrations are not needed to build the
# wheel, only src/ and README.md), then install the oryxenai project package.
COPY src/ ./src/
COPY README.md ./
RUN uv sync --frozen --no-dev

# ---- Stage 2: runtime ----
FROM python:3.13-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# The standalone Code Generator verifier is feature-disabled in the normal
# Docker overlay, but the image still carries the configured local toolchain so
# an explicitly enabled development profile does not silently fall back to a
# fake source check.
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm chromium \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user.
RUN groupadd --system --gid 1001 oryxen \
    && useradd --system --uid 1001 --gid oryxen --home-dir /app oryxen

WORKDIR /app

# Copy the fully-populated virtual environment from the builder.
COPY --from=builder --chown=oryxen:oryxen /app/.venv /app/.venv

# Copy runtime assets: source, config, migrations, entrypoint.
COPY --chown=oryxen:oryxen src/ ./src/
# The Vite output is generated in the image rather than relying on an ignored
# local build directory being present in the Docker build context.
COPY --from=frontend-builder --chown=oryxen:oryxen /app/src/oryxenai/web/static/product/ ./src/oryxenai/web/static/product/
COPY --chown=oryxen:oryxen config/ ./config/
COPY --chown=oryxen:oryxen migrations/ ./migrations/
COPY --chown=oryxen:oryxen alembic.ini ./
COPY --chown=oryxen:oryxen scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh

# Named preview/image-cache volumes are mounted over these paths at runtime.
# Seed them with the worker's ownership so Docker's first volume copy-up does
# not leave the non-root worker unable to promote a verified candidate.
RUN sed -i 's/\r$//' ./scripts/docker-entrypoint.sh \
    && mkdir -p /app/.workspace/code-generator-preview /app/.workspace/image-search-cache \
    && chown -R oryxen:oryxen /app/.workspace \
    && chmod +x ./scripts/docker-entrypoint.sh

USER oryxen

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health/live').read(); sys.exit(0)" || exit 1

ENTRYPOINT ["./scripts/docker-entrypoint.sh"]
CMD ["uvicorn", "oryxenai.main:app", "--host", "0.0.0.0", "--port", "8000"]
