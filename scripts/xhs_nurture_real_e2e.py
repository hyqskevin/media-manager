#!/usr/bin/env -S uv run --project ../backend python
"""小红书真实养号 e2e：

1. 检查 dev-api 在 8000 端口
2. 用 admin 登录拿 JWT
3. 创建 xhs 账号（session_name="e2e-real"）
4. POST /check-login -> 期望 logged_in=true（前提：storage_state 已存）
5. POST /nurture (actions=[browse_home, fetch_favorites], duration=3)
6. 轮询 /api/v1/nurture/history 找到这条任务 -> 状态变 completed
7. GET /platform-accounts/{id}/favorites -> 断言 item_count > 0

依赖：
    - dev-api 在跑（make dev-api）
    - dev-worker 在跑（make dev-worker；否则 Celery 任务不动）
    - data/storage_states/xhs_e2e.json 已存在（先跑 scripts/xhs_login_setup.py e2e）
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx  # pyproject 已有

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

API = "http://127.0.0.1:8000/api/v1"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.environ.get("INITIAL_ADMIN_PASSWORD", "Admin@123")
ACCOUNT_LABEL = os.environ.get("XHS_E2E_LABEL", "e2e")
STORAGE_STATE = ROOT_DIR / "data" / "storage_states" / f"xhs_{ACCOUNT_LABEL}.json"

ACCOUNT_NAME = f"e2e-real-{int(time.time())}"
TIMEOUT_S = 180  # 真实养号（browse 30s + fetch 60s + 启动）


def die(msg: str, code: int = 1) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(code)


def step(title: str) -> None:
    print(f"\n──── {title} ────")


def main() -> int:
    step("pre-flight")
    if not STORAGE_STATE.exists():
        die(
            f"storage_state 不存在: {STORAGE_STATE}\n"
            f"先跑: uv run --project ../backend python scripts/xhs_login_setup.py {ACCOUNT_LABEL}"
        )
    try:
        r = httpx.get(f"{API}/platforms", timeout=5)
        if r.status_code != 200:
            die(f"dev-api 不健康: GET /platforms -> {r.status_code}")
    except Exception as e:
        die(f"无法连接 dev-api ({API}): {e}\n先跑: make dev-api + make dev-worker")

    step("1) admin login")
    r = httpx.post(
        f"{API}/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    if r.status_code != 200:
        die(f"登录失败: {r.status_code} {r.text}")
    token = r.json()["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    print(f"     ✓ token={token[:24]}...")

    step("2) create xhs account")
    r = httpx.post(
        f"{API}/platform-accounts",
        json={"name": ACCOUNT_NAME, "platform": "xhs"},
        headers=H, timeout=10,
    )
    if r.status_code != 201:
        die(f"创建账号失败: {r.status_code} {r.text}")
    account_id = r.json()["id"]
    print(f"     ✓ account_id={account_id}, name={ACCOUNT_NAME}")

    step("3) check-login")
    # 把 storage_state 软链接成 session_name 对应的 storage_state
    # 简单起见，nurture_task.py 期望 storage_state 路径存在；
    # v0.2 实现里 storage_state 路径以 PlatformAccount.session_name 命名
    # 实际从 xhs_accounts 迁移过来的 session_name 是 "xhs-<uuid>"
    # 我们把当前 storage_state 复制成 session_name.json
    from app.core.database import SessionLocal  # noqa: PLC0415
    from app.models.platform_account import PlatformAccount  # noqa: PLC0415
    session = SessionLocal()
    try:
        acc = session.get(PlatformAccount, account_id)
        target_state = ROOT_DIR / "data" / "storage_states" / f"{acc.session_name}.json"
        if not target_state.exists():
            target_state.write_bytes(STORAGE_STATE.read_bytes())
            print(f"     ✓ copied storage_state -> {target_state.name}")
    finally:
        session.close()

    r = httpx.post(f"{API}/platform-accounts/{account_id}/check-login", headers=H, timeout=60)
    if r.status_code != 200:
        die(f"check-login 失败: {r.status_code} {r.text}")
    result = r.json()
    print(f"     ✓ logged_in={result.get('logged_in')} user_id={result.get('user_id')!r}")
    if not result.get("logged_in"):
        die(f"未检测到登录，可能 storage_state 失效：{result.get('error')}")

    step("4) enqueue nurture task")
    r = httpx.post(
        f"{API}/platform-accounts/{account_id}/nurture",
        json={"actions": ["browse_home", "fetch_favorites"], "duration_minutes": 5},
        headers=H, timeout=15,
    )
    if r.status_code != 200:
        die(f"启动养号失败: {r.status_code} {r.text}")
    celery_task_id = r.json()["task_id"]
    print(f"     ✓ celery_task_id={celery_task_id}")

    step("5) poll task status -> completed")
    deadline = time.time() + TIMEOUT_S
    final_status = None
    history = None
    while time.time() < deadline:
        time.sleep(5)
        r = httpx.get(f"{API}/nurture/history", headers=H, timeout=10)
        if r.status_code != 200:
            continue
        items = r.json()
        history = next((t for t in items if t["celery_task_id"] == celery_task_id), None)
        if history:
            final_status = history["status"]
            print(f"     ...status={final_status} (waited {int(TIMEOUT_S - (deadline - time.time()))}s)")
            if final_status in {"completed", "failed", "skipped"}:
                break

    if not history:
        die(f"{TIMEOUT_S}s 内未在 history 找到任务 {celery_task_id}")
    if final_status != "completed":
        die(f"任务未 completed：status={final_status}, error={history.get('error')}")
    print(f"     ✓ completed in {history.get('finished_at')}")
    print(f"        started={history.get('started_at')}  items_collected={history.get('items_collected')}")

    step("6) fetch favorites snapshot")
    r = httpx.get(f"{API}/platform-accounts/{account_id}/favorites", headers=H, timeout=10)
    if r.status_code != 200:
        die(f"favorites 失败: {r.status_code} {r.text}")
    snap = r.json()
    item_count = snap.get("item_count", 0)
    print(f"     ✓ item_count={item_count}, captured_at={snap.get('captured_at')}")
    if item_count == 0:
        die(f"item_count=0 — fetch_favorites 真实抓取失败（snapshot error={snap.get('error')!r}）")

    step("✅ ALL PASSED")
    print(f"   account_id={account_id}")
    print(f"   favorites item_count={item_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())