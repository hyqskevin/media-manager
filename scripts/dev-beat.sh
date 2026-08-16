#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 只 grep 读取启动参数，不 source 全部 .env
LOG_LEVEL="$(grep -E '^CELERY_LOG_LEVEL=' .env 2>/dev/null | head -1 | cut -d= -f2- || true)"
CELERY_FOLDER="$(grep -E '^CELERY_FOLDER=' .env 2>/dev/null | head -1 | cut -d= -f2- || true)"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
CELERY_FOLDER="${CELERY_FOLDER:-./data/celery}"

exec uv run --project backend celery -A app.tasks.celery_app:celery_app beat --loglevel="$LOG_LEVEL" --schedule "$CELERY_FOLDER/celerybeat-schedule"
