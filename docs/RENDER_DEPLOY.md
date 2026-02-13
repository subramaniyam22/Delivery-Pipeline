# Render deployment

## Services

- **delivery-backend** — Web (Python). Start: `alembic upgrade head && gunicorn app.main:app ...`
- **delivery-worker** — Background worker. Runs `python -m app.jobs.worker`; polls generic `jobs` table and project-stage JobRun, writes heartbeat to Redis.
- **delivery-frontend** — Next.js.
- **delivery-db** (Postgres), **delivery-redis** (Redis).

## Required env vars (backend + worker)

Set in Render Dashboard for both backend and worker so they stay in sync:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | From Render Postgres (connection string). |
| `REDIS_URL` | From Render Redis. |
| `SECRET_KEY` | Same value on backend and worker (JWT, etc.). |
| `OPENAI_API_KEY` | Required for blueprint generation and AI. |
| `OPENAI_MODEL` | e.g. `gpt-4o`. |
| `OPENAI_TEMPERATURE` | e.g. `0.2`. |
| `STORAGE_BACKEND` | `local` or `s3`. |
| S3_* | If using S3: `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`. |

Optional: `OPENAI_MODEL_FALLBACK`, `OPENAI_MAX_TOKENS`, `OPENAI_TIMEOUT_SECONDS`.

## Release command (backend)

Backend blueprint uses **Start Command** to run migrations:

```
alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 60
```

No separate Release Command is required unless you prefer migrations in a release phase.

## Worker

- Worker must run as a **separate service** (Background Worker on Render).
- Same env as backend (especially `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`).
- Worker writes heartbeat to Redis every 10s (`worker:heartbeat:delivery-worker`). Backend `/health` and `/system/health` use this for `worker_ok` / `worker_healthy`.
- If worker is down, blueprint jobs stay in `jobs` table (queued/retry) until the worker is back.

## Blueprint generation in prod

1. User clicks **Generate Blueprint** in Template Registry.
2. Backend creates a run and enqueues a job (no BackgroundTasks).
3. Worker picks up the job, runs blueprint generation, updates the run.
4. UI polls and shows status; on failure, "View details" shows run error and debug info.

## Verifying

- **Backend**: Open `https://<backend>.onrender.com/health` — expect `worker_ok: true` when worker is running.
- **Blueprint**: Create a template, trigger Generate Blueprint, confirm status moves to ready or failed with a clear message.
- **Logs**: Worker logs include "Generic job started" / "Generic job completed" and heartbeat activity.
