# Deploying to Render

This doc covers backend, worker, and frontend on Render with **migrations on deploy** and a **Docker-based worker** (Node 20, Lighthouse, Chromium, Playwright).

## Architecture

| Service           | Type  | Runtime | Notes |
|-------------------|-------|---------|--------|
| delivery-backend  | web   | Python  | Migrations via **preDeployCommand**. Health: `/health`. |
| delivery-frontend | web   | Node 20 | Next.js. |
| delivery-worker   | worker| **Docker** | Uses `worker/Dockerfile` (Python + Node + Lighthouse + Playwright). |
| delivery-redis    | redis | —       | Key Value. |
| delivery-db       | Postgres | —    | Database. |

The worker **must** be Docker-based on Render so it includes Node, Lighthouse, and Chromium; the native Python runtime does not provide them.

## Backend: migrations on deploy

- **Free tier:** Render does not support Pre-Deploy Command on free tier. The blueprint runs migrations in the **Start Command**: `alembic upgrade head && gunicorn ...`, so migrations run when the app starts.
- **Paid tier:** You can move migrations to **Pre-Deploy Command** in the dashboard (or in `render.yaml` with `preDeployCommand: alembic upgrade head`) so they run before the new instance starts.
- Optional: to seed data once, run from Render shell or a one-off job: `python -m scripts.seed.seed_all_prod`.

If you configure the service in the Dashboard instead of the blueprint, set **Pre-Deploy Command** to:

```bash
alembic upgrade head
```

and **Start Command** to:

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 60 --keep-alive 5
```

(Do not run migrations inside the start command.)

## Worker: Docker image

The worker is defined in `render.yaml` with:

- **runtime**: `docker`
- **dockerfilePath**: `worker/Dockerfile`
- **dockerContext**: `.` (repo root)

The worker image includes:

- Python 3.11 + backend dependencies
- Node 20
- Lighthouse + @lhci/cli
- Chromium (system package)
- Playwright + Chromium

On startup the worker logs **node_version**, **lighthouse_version**, and **playwright_chromium**, then **Worker ready** after connecting to DB and Redis. Use these logs to confirm the container has the right tools.

## Environment variables

Set these in the Render Dashboard (Environment tab) for each service. The blueprint already provides many; override or add as below.

### Backend (delivery-backend)

| Variable | Required | Notes |
|----------|----------|--------|
| DATABASE_URL | ✓ | From blueprint (delivery-db) |
| REDIS_URL | ✓ | From blueprint (delivery-redis) |
| SECRET_KEY | ✓ | From blueprint (generated) or set your own |
| CORS_ORIGINS | ✓ | Your frontend URL(s), comma-separated |
| FRONTEND_URL | ✓ | Frontend URL |
| BACKEND_URL | ✓ | This backend’s URL (for preview links, webhooks) |
| ENVIRONMENT | ✓ | `production` |
| OPENAI_API_KEY | Recommended | For AI agents and template jobs |
| STORAGE_BACKEND | — | `local` or `s3` |
| S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION | If S3 | Same as worker |
| RESEND_API_KEY | Optional | Email (onboarding, completion) |
| SENTRY_DSN | Optional | Error tracking |

### Worker (delivery-worker)

| Variable | Required | Notes |
|----------|----------|--------|
| DATABASE_URL | ✓ | From blueprint |
| REDIS_URL | ✓ | From blueprint |
| SECRET_KEY | ✓ | **Must match backend** (same value) |
| FRONTEND_URL | ✓ | Frontend URL |
| BACKEND_URL | ✓ | Backend URL |
| ENVIRONMENT | ✓ | `production` |
| STORAGE_BACKEND | ✓ | Same as backend (`local` or `s3`) |
| S3_* | If S3 | Same bucket/credentials as backend |
| OPENAI_API_KEY | Recommended | For Build/Test stages |
| LIGHTHOUSE_ENABLED, AXE_ENABLED, PLAYWRIGHT_ENABLED | — | Blueprint sets `true`; override if needed |
| PREVIEW_THUMBNAIL_MODE | — | `playwright` (blueprint) or `simple` |

Do **not** set CORS_ORIGINS or CORS_ORIGIN_REGEX on the worker (backend only).

### Frontend (delivery-frontend)

| Variable | Required | Notes |
|----------|----------|--------|
| NEXT_PUBLIC_API_URL | ✓ | Backend URL (e.g. `https://delivery-backend.onrender.com`) |

## S3 (optional)

For persistent storage (uploads, previews), set **STORAGE_BACKEND=s3** on **both** backend and worker and configure the same S3 (or S3-compatible) credentials and bucket. See **docs/RENDER_ENV.md** for S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION, and optional S3_ENDPOINT_URL (e.g. R2).

## Deploy order

1. Ensure **delivery-db** and **delivery-redis** exist (blueprint creates them).
2. Deploy **delivery-backend** first (migrations run in preDeployCommand).
3. Deploy **delivery-worker** (Docker build can take a few minutes).
4. Deploy **delivery-frontend** (set NEXT_PUBLIC_API_URL to backend URL).

After first deploy, set **BACKEND_URL** and **FRONTEND_URL** in the Dashboard to the actual URLs if they differ from the blueprint defaults, then redeploy backend and worker so links and CORS are correct.

## Health and logs

- **Backend**: `GET https://<backend-url>/health` returns `status`, `checks.database`, `checks.redis`, `checks.storage`. Use this as the health check path (blueprint sets `healthCheckPath: /health`).
- **Worker**: No HTTP endpoint; confirm readiness via logs. Look for `Worker ready` and version lines (`node_version`, `lighthouse_version`, `playwright_chromium`).

## Render settings summary

| Setting | Backend | Worker | Frontend |
|---------|---------|--------|----------|
| **Release / Pre-deploy** | `alembic upgrade head` | — | — |
| **Start command** | `gunicorn app.main:app ...` | (Dockerfile CMD) | `next start ...` |
| **Worker runtime** | — | **Docker** (`worker/Dockerfile`) | — |
| **Health check path** | `/health` | — | — |

All of the above are already set in **render.yaml**; you only need to add or override environment variables in the Dashboard as needed.
