#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT_DIR"
set -a; source .env; set +a
exec uv run --project backend python -c 'from pathlib import Path; from app.core.config import get_settings; from app.services.maintenance import backup_sqlite; s=get_settings(); print(backup_sqlite(s.sqlite_path, Path("'"$BACKUP_DIR"'")))'
