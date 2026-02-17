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

# Install Node.js 20 LTS and git for code execution and version control
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates git && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy agent source code
COPY agent/ agent/

ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "agent.main:create_app", "--host", "0.0.0.0", "--port", "8080", "--factory"]
