# Local development with Docker

Run the full stack (Postgres, Redis, Backend, Worker, Frontend) with a single command. All dependencies—including Node 20, Lighthouse, Chromium, and Playwright—live inside containers; no need to install them on your host.

## Prerequisites

- **Docker Desktop** (or Docker Engine + Docker Compose v2)
- **Git**
- Optional: **.env** file (copy from `.env.example`) for `OPENAI_API_KEY`, etc.

## Quick start

```bash
# From repo root
cp .env.example .env
# Edit .env if needed (e.g. OPENAI_API_KEY for AI features)

docker compose up --build
```

This starts:

| Service   | Port  | Description                    |
|----------|-------|--------------------------------|
| postgres | 5433→5432 | Database                      |
| redis    | 6379  | Cache / job queue              |
| backend  | 8000  | FastAPI (migrations run on startup) |
| worker   | —     | Job runner (Lighthouse, Playwright)  |
| frontend | 3000  | Next.js                        |

- **Backend**: Migrations run automatically via `backend/scripts/entrypoint.sh`, then Uvicorn with `--reload`.
- **Worker**: Logs `node_version`, `lighthouse_version`, `playwright_chromium`, then `Worker ready` when DB and Redis are connected.

## Commands

| Task | Command |
|------|--------|
| Start all | `docker compose up --build` |
| Start in background | `docker compose up -d --build` |
| View logs | `docker compose logs -f` (all) or `docker compose logs -f backend` (one service) |
| Stop all | `docker compose down` |
| Run migrations only | `docker compose run --rm backend alembic upgrade head` |
| Seed DB (optional) | `docker compose run --rm backend python -m scripts.seed.seed_all_demo` (or `seed_all_prod`) |
| Shell in backend | `docker compose exec backend sh` |
| Shell in worker | `docker compose exec worker sh` |

## Environment variables

See **.env.example** at repo root. Copy to `.env` and set at least:

- `OPENAI_API_KEY` – required for AI agents and template blueprint/validation jobs.
- Others have defaults suitable for local (e.g. `DATABASE_URL` is overridden by compose for in-container URLs).

Backend and worker both read the same vars (e.g. `DATABASE_URL`, `REDIS_URL`, `STORAGE_BACKEND`, `LIGHTHOUSE_ENABLED`). Compose injects service names (`postgres`, `redis`) so no change needed for local.

## Health and readiness

- **Backend**: `GET http://localhost:8000/health` returns `db`, `redis`, and `storage` checks.
- **Worker**: Look for `Worker ready` in logs: `docker compose logs worker`.

## Troubleshooting

### "Network Error" / `net::ERR_EMPTY_RESPONSE` on login

The frontend (localhost:3000) cannot reach the backend (localhost:8000). Do this:

1. **Check backend is running**
   ```bash
   docker compose ps
   ```
   Ensure `delivery_backend` (or `backend`) is **Up**. If it’s Exit or Restarting, check logs (step 2).

2. **Check backend logs**
   ```bash
   docker compose logs backend
   ```
   Look for:
   - `Migrations complete.` then Uvicorn listening (backend started OK).
   - `column ... does not exist` → run migrations: `docker compose run --rm backend alembic upgrade head` then `docker compose restart backend`.
   - `exec ... entrypoint.sh: no such file or directory` → ensure `backend/scripts/entrypoint.sh` has LF line endings (see Known pitfalls).

3. **Hit the backend directly**
   In the browser open: `http://localhost:8000/health`  
   - If it loads (JSON with `status`, `checks`), the backend is up; the problem may be CORS or the login route.
   - If it fails or never loads, the backend is not reachable (not running, wrong port, or firewall).

4. **Restart the stack**
   ```bash
   docker compose down
   docker compose up -d
   docker compose logs -f backend
   ```
   Then try `http://localhost:8000/health` and login again.

## Known pitfalls

1. **OneDrive / cloud-synced folders**  
   If the repo lives under OneDrive or similar, Docker bind mounts (e.g. `./backend:/app`) can cause slow or inconsistent behavior. Prefer a local path outside sync (e.g. `C:\dev\Delivery-Pipeline` on Windows).

2. **Ports in use**  
   If 3000, 5433, 6379, or 8000 are already in use, change them in `docker-compose.yml` (left side of `ports`) or stop the conflicting service.

3. **Worker not running**  
   Ensure the **worker** service builds from `worker/Dockerfile` (context: repo root). If you see “Lighthouse CLI not found” in job logs, the worker image may be the old backend-only image; run `docker compose build worker` and `docker compose up -d`.

4. **Migrations**  
   Migrations run automatically when the backend container starts (entrypoint). To run them manually: `docker compose run --rm backend alembic upgrade head` (this starts postgres/redis if needed, so the backend can resolve hostname `postgres`). If you see **`column job_runs.correlation_id does not exist`** (or other missing-column errors), run the same command, then restart the backend: `docker compose restart backend`.

5. **"could not translate host name postgres to address"**  
   The backend uses the hostname `postgres` (the Compose service name) for the database. That only resolves when the backend runs on the same Compose network as the postgres service. Start the full stack so all services share the network: `docker compose up -d` (or `docker compose up --build`). Do not start only the backend container in isolation.

## Optional: hot reload without full rebuild

The default compose mounts `./backend` and `./frontend` so you can edit code and see changes (backend reloads via Uvicorn, frontend via Next.js dev server). For a production-like run without mounts, comment out the `volumes` for backend and frontend and rely on the built image only.
