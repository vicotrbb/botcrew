# Botcrew Orchestrator - Multi-stage Docker build
# Stage 1: Build dependencies with uv
# Stage 2: Minimal runtime image

# ---------------------------------------------------------------------------
# Builder stage: install Python dependencies with uv
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install production dependencies only (no dev group)
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src/ src/

# Install the project itself into the venv
RUN uv sync --frozen --no-dev

# ---------------------------------------------------------------------------
# Runtime stage: slim image with only what's needed
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy alembic configuration and migrations (for migration jobs)
COPY alembic.ini ./
COPY alembic/ alembic/

# Copy source code
COPY src/ src/

# Ensure the venv is on PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "botcrew.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
