# ==============================================================================
# Botcrew Browser Sidecar Container
# ==============================================================================
# Based on official Playwright Python image with browsers pre-installed.
# Runs as a K8s native sidecar alongside the agent container, sharing the
# pod's localhost network. Exposes Playwright operations via HTTP API at
# port 8001.
#
# The Playwright base image is large (~1.9GB) because it includes Chromium,
# Firefox, and WebKit browsers plus all required system dependencies.
# ==============================================================================

FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Create non-root user
RUN groupadd -r botcrew && useradd -r -g botcrew -s /bin/bash -m botcrew

# Install only curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create workspace directory
RUN mkdir -p /workspace && chown -R botcrew:botcrew /workspace

# Copy requirements and install Python dependencies
COPY --chown=botcrew:botcrew requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r /workspace/requirements.txt

# Copy API application
COPY --chown=botcrew:botcrew api/ /workspace/api/

# Copy entrypoint script
COPY --chown=botcrew:botcrew entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Ensure Python can find the API modules
ENV PYTHONPATH="/workspace/api:$PYTHONPATH"

# Switch to non-root user
USER botcrew
WORKDIR /workspace

# Expose API port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health || exit 1

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
