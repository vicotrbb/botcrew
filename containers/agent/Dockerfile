# Botcrew Agent Container - Multi-stage Docker build
# Stage 1: Build dependencies with uv
# Stage 2: Minimal runtime image

# ---------------------------------------------------------------------------
# Builder stage: install Python dependencies with uv
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency file first for layer caching
COPY requirements.txt ./

# Install production dependencies into the system Python
RUN uv pip install --system -r requirements.txt

# ---------------------------------------------------------------------------
# Runtime stage: slim image with only what's needed
# ---------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy agent source code
COPY agent/ agent/

ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "agent.main:create_app", "--host", "0.0.0.0", "--port", "8080", "--factory"]
