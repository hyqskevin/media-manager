#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command -v uv >/dev/null || { echo "缺少 uv，请先安装：https://docs.astral.sh/uv/"; exit 1; }
command -v node >/dev/null || { echo "缺少 Node.js 22+"; exit 1; }
command -v npm >/dev/null || { echo "缺少 npm"; exit 1; }

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "已创建 .env，请按需填写 SECRET_KEY、OPENCLI_CDP_ENDPOINT 和 MINIMAX_API_KEY。"
fi

while IFS= read -r line; do
  if [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
    key="${line%%=*}"
    if ! grep -q "^${key}=" .env; then
      printf '\n%s\n' "$line" >> .env
    fi
  fi
done < .env.example

set -a
source "$ROOT_DIR/.env"
set +a

uv sync --project backend --python 3.11 --extra ocr
npm --prefix frontend install
uv run --project backend --extra ocr python -c "import os; from app.core.config import get_settings; from app.core.database import SessionLocal,init_database; from app.services.maintenance import create_admin; get_settings().ensure_runtime_directories(); init_database(); db=SessionLocal(); create_admin(db,os.environ['ADMIN_USERNAME'],os.environ['ADMIN_PASSWORD']); db.close()"

echo "初始化完成。使用 make dev-api、make dev-worker、make dev-beat、make dev-web 分别启动服务。"
