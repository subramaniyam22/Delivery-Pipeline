# Local development

## Run full stack (Docker)

```bash
# From repo root
docker compose up --build
```

Brings up:
- **postgres** (port 5433 → 5432)
- **redis** (6379)
- **backend** (8000) — runs migrations on startup via uvicorn
- **worker** — runs `python -m app.jobs.worker` (polls generic jobs + project-stage JobRun, writes heartbeat to Redis)
- **frontend** (3000)

## Verify worker and health

1. **Health**
   ```bash
   curl -s http://localhost:8000/health | jq
   ```
   Expect `worker_ok: true` and `checks.worker: "ok"` once the worker container is running and writing heartbeats (`worker:heartbeat:delivery-worker`).

2. **System health**
   ```bash
   curl -s http://localhost:8000/system/health | jq
   ```
   Same; `worker_healthy: true` when heartbeat age < 60s.

## Blueprint generation (no manual enqueue in backend)

1. Open Configuration → Template Registry, select a template, Blueprint tab.
2. Click **Generate Blueprint**. Backend creates a run and enqueues a job to the generic `jobs` table (type `template.blueprint.generate`).
3. Worker claims the job, runs blueprint generation, updates the run (status → generating → validating → ready/failed).
4. UI polls `/api/templates/{id}/blueprint/status` (or `/blueprint-job`) and shows status + "View details" on failure.

If **worker is not running**, `worker_ok` is false and the UI shows "Worker is offline. Blueprint jobs will not execute."

## Run backend only (no Docker)

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Unix: source venv/bin/activate
pip install -r requirements.txt
# Set DATABASE_URL, REDIS_URL, OPENAI_API_KEY, etc. (see .env.example)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Run worker in another terminal (same env):

```bash
cd backend
python -m app.jobs.worker
```

## Run tests

```bash
cd backend
pytest tests/ -v
```
