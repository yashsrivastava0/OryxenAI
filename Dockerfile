# Multi-stage Dockerfile for the OryxenAI application image.
# Serves the FastAPI API plus the compiled authenticated Preact product shell.

# ---- Stage 0: product frontend ----
FROM node:22-bookworm-slim@sha256:48e4b67d85f87bd551df43704e24d252f56cc5f8e9718841aace50f19948f0f9 AS frontend-builder

WORKDIR /app/frontend

# Install from the lockfile before copying source so dependency layers remain
# cacheable while every image build produces the manifest-backed product bundle.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

# The product frontend imports the canonical Living Draft mark from the
# server-owned auth static tree. Copy that shared source into the builder at
# the path expected by the relative import before TypeScript runs.
COPY src/ /app/src/
COPY frontend/ ./
RUN npm run build

# ---- Stage 1: builder ----
FROM python:3.13-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26 AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=3.13

# Install uv using the official standalone binary method.
COPY --from=ghcr.io/astral-sh/uv:0.11.19@sha256:b46b03ddfcfbf8f547af7e9eaefdf8a39c8cebcba7c98858d3162bd28cf536f6 /uv /uvx /bin/

WORKDIR /app

ARG PDF_ENGINE=light

# RapidOCR pulls OpenCV's manylinux wheel. Supply the small set of Debian
# runtime libraries it expects even though the app never opens a GUI.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 libgl1 libxcb1 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency manifests for cache-efficient install.
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment (no dev deps, no project).
RUN if [ "$PDF_ENGINE" = "full" ]; then \
        uv sync --frozen --no-dev --no-install-project --extra pdf-full; \
    else \
        uv sync --frozen --no-dev --no-install-project; \
    fi

# Download the exact CPU OCR/layout assets into the image. Runtime requests do
# not contact Hugging Face or any OCR service.
COPY scripts/download_docling_models.py ./scripts/download_docling_models.py
RUN mkdir -p /opt/docling-models \
    && if [ "$PDF_ENGINE" = "full" ]; then \
        uv run --no-sync python scripts/download_docling_models.py --output-dir /opt/docling-models; \
    fi

# Copy application source (config/migrations are not needed to build the
# wheel, only src/ and README.md), then install the oryxenai project package.
COPY src/ ./src/
COPY README.md ./
RUN if [ "$PDF_ENGINE" = "full" ]; then \
        uv sync --frozen --no-dev --extra pdf-full; \
    else \
        uv sync --frozen --no-dev; \
    fi

# ---- Stage 2: runtime ----
FROM python:3.13-slim-bookworm@sha256:2325bb286ec344af3e5898cc224b5844e2707ac6e26b1632516fd3edc84a5e26 AS runtime

# Required by the OpenCV wheel used by the light OCR engine.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 libgl1 libxcb1 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Optional: headless Chromium so generated portfolio pages are also verified in a
# real browser before they go live. Off by default (the image stays small); build
# with --build-arg INSTALL_CHROMIUM=true and set
# [code_generator.verification] browser = "best_effort" in the deployment overlay.
ARG INSTALL_CHROMIUM=false

ENV PATH="/app/.venv/bin:${PATH}" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DOCLING_ARTIFACTS_PATH=/opt/docling-models \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    OMP_NUM_THREADS=2 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create a non-root user.
RUN groupadd --system --gid 1001 oryxen \
    && useradd --system --uid 1001 --gid oryxen --home-dir /app oryxen

WORKDIR /app

# Copy the fully-populated virtual environment from the builder.
COPY --from=builder --chown=oryxen:oryxen /app/.venv /app/.venv
COPY --from=builder --chown=oryxen:oryxen /opt/docling-models/ /opt/docling-models/
# Copy runtime assets: source, config, migrations, entrypoint.
COPY --chown=oryxen:oryxen src/ ./src/
# The Vite output is generated in the image rather than relying on an ignored
# local build directory being present in the Docker build context.
COPY --from=frontend-builder --chown=oryxen:oryxen /app/src/oryxenai/web/static/product/ ./src/oryxenai/web/static/product/
COPY --chown=oryxen:oryxen config/ ./config/
COPY --chown=oryxen:oryxen migrations/ ./migrations/
COPY --chown=oryxen:oryxen alembic.ini ./
COPY --chown=oryxen:oryxen scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh

# Keep application-owned paths writable by the non-root service account.
RUN sed -i 's/\r$//' ./scripts/docker-entrypoint.sh \
    && mkdir -p /app/.workspace/archive-storage \
        /app/.workspace/archive-artifacts /app/.workspace/archive-generation \
        /app/.workspace/archive-checkpoints /app/.workspace/archive-workspaces \
        /app/.workspace/archive-handoffs /app/output/archive-exports \
        /app/output/archive-handoff-mirrors \
    && chown -R oryxen:oryxen /app/.workspace \
        /app/output \
    && chmod +x ./scripts/docker-entrypoint.sh

# Runs as root (system packages), before dropping to the service account.
RUN if [ "$INSTALL_CHROMIUM" = "true" ]; then \
        python -m playwright install --with-deps chromium \
        && chmod -R a+rX /ms-playwright; \
    fi

USER oryxen

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request,sys; port=os.environ.get('PORT','8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health/live').read(); sys.exit(0)" || exit 1

ENTRYPOINT ["./scripts/docker-entrypoint.sh"]
CMD ["sh", "-c", "exec uvicorn oryxenai.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
