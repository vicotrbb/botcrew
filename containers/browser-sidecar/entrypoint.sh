#!/bin/bash

# Botcrew Browser Sidecar Entrypoint
echo "Starting Botcrew Browser Sidecar..."
echo "Python version: $(python --version)"

# Note: Playwright browsers are pre-installed in the base image
# mcr.microsoft.com/playwright/python includes Chromium, Firefox, WebKit

# Start the API server
echo "Starting Browser Sidecar API on port ${BROWSER_PORT:-8001}..."
cd /workspace/api
exec python -m uvicorn main:app --host 0.0.0.0 --port ${BROWSER_PORT:-8001}
