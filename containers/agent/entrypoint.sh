#!/usr/bin/env bash
set -euo pipefail

exec uvicorn agent.main:create_app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --factory
