#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 只 grep 读取启动参数，不 source 全部 .env
WEB_HOST="$(grep -E '^WEB_HOST=' .env 2>/dev/null | head -1 | cut -d= -f2- || true)"
WEB_PORT="$(grep -E '^WEB_PORT=' .env 2>/dev/null | head -1 | cut -d= -f2- || true)"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-5173}"

exec npm --prefix frontend run dev -- --host "$WEB_HOST" --port "$WEB_PORT"
