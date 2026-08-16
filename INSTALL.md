# Install & Run media-manager

This document describes how to bring up the project on a fresh Linux/macOS machine for **development / local use**.

## 1. System Requirements

| Tool | Version | Used by |
|------|---------|---------|
| Python | ≥ 3.11 | backend |
| Node.js | ≥ 18 LTS | frontend |
| npm | bundled with Node | frontend |
| Git | any recent | source |
| macOS / Linux | OS | host |
| OpenCLI | latest | xhs crawler |
| Chrome | any recent | xhs login / opencli |
| (Optional) Make | any | shortcut targets |

> Windows users: install WSL2 and follow the Linux steps inside it.

## 2. Clone

```bash
git clone https://github.com/hyqskevin/xhs-info-crawl.git
cd xhs-info-crawl
# pick a release tag, e.g.
git checkout v0.3.0
```

## 3. Backend (FastAPI + Celery + SQLite)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[ocr]"           # ocr extra installs paddleocr / paddlepaddle
```

### 3.1 Initial database

```bash
export INITIAL_ADMIN_PASSWORD="ChangeMe123!"      # OPTIONAL: override default admin password
alembic upgrade head                                # apply all migrations
```

> Migration `0012_seed_admin` (TODO, not yet committed) inserts an `admin` user when none exists.
> Without that migration you must create the admin via the SQL insert described in [docs/database-design.md](docs/database-design.md).

### 3.2 Environment variables (optional)

| Variable | Default | Purpose |
|---|---|---|
| `XHS_BACKEND_HOST` | `0.0.0.0` | uvicorn bind |
| `XHS_BACKEND_PORT` | `8000` | uvicorn port |
| `INITIAL_ADMIN_PASSWORD` | `Admin@123` | seed admin password (production must override) |
| `OPENCLI_BROWSER_COMMAND_TIMEOUT` | `120` | seconds |
| `CELERY_BROKER_URL` | `filesystem:///abs/path/to/celery_broker` | phase one uses filesystem broker; stage two switches to Redis |
| `CELERY_RESULT_BACKEND` | `filesystem:///abs/path/to/celery_results` | phase one |

### 3.3 Start

In **three** terminals:

```bash
# terminal 1 — API
cd backend && source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# terminal 2 — celery worker
cd backend && source .venv/bin/activate
celery -A app.tasks.crawl_task worker --loglevel=info --concurrency=1

# terminal 3 — celery beat (for scheduled jobs)
cd backend && source .venv/bin/activate
celery -A app.tasks.crawl_task beat --loglevel=info
```

## 4. Frontend (Vue 3 + Vite)

```bash
cd frontend
npm ci
npm run dev          # http://localhost:5173 (dev with HMR)
# OR for production build:
npm run build
npm run preview      # http://localhost:4173
```

The frontend `.env` or its `vite.config.ts` must point at the backend URL. The default is `http://localhost:8000`.

## 5. First Use

1. Open `http://localhost:5173` (dev) or `http://localhost:4173` (preview).
2. Log in with username `admin` and password `Admin@123` (or whatever you set).
3. Configuration Center → add a city, keywords, bloggers.
4. Dashboard → start a crawl. Make sure Chrome is logged in to xhs.

## 6. Tests (optional, recommended before opening PRs)

```bash
# backend
cd backend && source .venv/bin/activate
pytest -q

# frontend
cd frontend
npm run test -- --run
npm run build
```

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: app.xxx` | make sure you are in `backend/` and the venv is active |
| Celery task never runs | check broker dir is writable; check `celery beat` is also running |
| OpenCLI error `Missing url` | some bloggers need their `profile_url` filled; "补充博主信息" on Settings |
| Frontend can't reach backend | verify CORS / `VITE_API_BASE` / proxy config |

## 8. Where Next

- `docs/TODO.md` — open issues
- `AGENTS.md` — AI agent flow
- `docs/superpowers/specs/` — design specs
- `tests/*.md` — E2E specs

## 9. Packaged Build (Non-Developers)

If you are an end user (not a developer), you do not need to install Python, Node.js, or any build toolchain. Use the pre-built packages instead.

### 9.1 Download

1. Go to the [Releases page](https://github.com/hyqskevin/xhs-info-crawl/releases).
2. Find the latest version.
3. Download the zip for your platform:
   - macOS (Apple Silicon): `xhs-info-crawl-<version>-macos.zip`
   - Windows: `xhs-info-crawl-<version>-windows.zip`
   - Source code (developers): `xhs-info-crawl-<version>-src.zip`

### 9.2 Install

- **macOS**: Unzip, then right-click `xhs-info-crawl.app` → "Open" → confirm "Open" in the Gatekeeper dialog (first launch only). Subsequent launches: double-click the `.app`.
- **Windows**: Unzip, then double-click `start.bat` inside the `xhs-info-crawl` folder.

### 9.3 Differences from Developer Install

| Aspect | Developer | Packaged |
|---|---|---|
| Python | System install (3.11+) | Bundled `runtime/python/` (cpython-3.11.9) |
| Node.js | Required (18+) | Not needed (frontend pre-built) |
| Dependencies | `pip install -e ".[ocr]"` | Pre-installed in `runtime/venv/` |
| Frontend | `npm run dev` | Served by FastAPI StaticFiles |
| Launcher | N/A | PyWebView window (separate from web UI) |
| OCR | Included via `[ocr]` extra | Separate add-on zip (one-click install) |

### 9.4 Upgrade

1. Download the new version zip.
2. Replace the application files (everything except the `data/` directory).
3. Keep your existing `data/` directory to preserve all crawled data, settings, and database.
4. If upgrading across major versions, check the release notes for migration steps.

### 9.5 User Guide

For the full end-user guide (OpenCLI setup, OCR install, daily usage), see [README-USER.md](README-USER.md).

