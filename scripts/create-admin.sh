#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT_DIR"
set -a; source .env; set +a
: "${ADMIN_USERNAME:?Set ADMIN_USERNAME in .env}"
: "${ADMIN_PASSWORD:?Set ADMIN_PASSWORD in .env}"
exec uv run --project backend python -c 'from app.core.database import SessionLocal,init_database; from app.services.maintenance import create_admin; init_database(); db=SessionLocal(); create_admin(db,"'"$ADMIN_USERNAME"'","'"$ADMIN_PASSWORD"'"); db.close(); print("admin ready")'
