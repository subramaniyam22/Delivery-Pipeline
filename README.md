# Delivery Automation Suite MVP

Production-ready MVP with **FastAPI + LangGraph** backend, **Next.js (App Router)** frontend, and strict **role-based access control (RBAC)**.

## 🎯 Overview

A multi-agent workflow system with 6 stages plus AI template management:
1. **Project Onboarding** - Initial project setup and documentation
2. **Project Assignment** - Task assignment and resource allocation
3. **Build** - Development work (Human-in-the-loop optional)
4. **Test** - Quality assurance and testing
5. **Defect Validation** - Defect analysis and validation
6. **Complete** - Project closure and summary

Key capabilities:
- AI-driven workflow orchestration with optional human approval gates (global and per-project)
- AI template registry with preview generation and publish/unpublish controls
- SLA configuration, quality thresholds, and preview strategy management in admin UI
- Operations dashboard for job queue health, retries, and stuck runs
- Quality dashboard and client sentiment tracking
- Auto-advance from Sales to Onboarding when all required fields are complete (Drafts stay in Sales until activated)
- Multi-location support (`location_names`) and stage timeline history (`stage_history`)
- Notifications, audit logs, and admin configuration UI
- Chat log webhooks for external systems and training pipelines
- JWT-secured notification WebSocket connections
- Debug endpoints gated in production

## 🔐 Roles & Permissions

| Role | Permissions |
|------|-------------|
| **Admin** | Full access to all endpoints and UI pages |
| **Manager** | Full access + can edit workflow config values |
| **Consultant** | Create projects, update onboarding, view status |
| **PC (Project Coordinator)** | Task assignment access, manage assignment stage |
| **Builder** | Build stage access only (start/progress/complete, upload artifacts) |
| **Tester** | Test stage access only (start/progress/complete, upload reports, create defects) |
| **Sales** | Create projects, manage sales-stage data, save drafts |

## 🏗️ Architecture

### Backend (FastAPI + LangGraph)
- **FastAPI** for REST API
- **LangGraph** for multi-agent workflow orchestration
- **PostgreSQL** for data persistence
- **SQLAlchemy 2.0** + Alembic for database management
- **JWT** authentication with 6-hour expiry
- **RBAC** enforcement on all endpoints
- **Structured logging** with request IDs
- **Webhook** delivery for chat logs

### Frontend (Next.js)
- **Next.js 16** with App Router
- **TypeScript** for type safety
- **Axios** for API communication
- **Role-based UI** rendering

## 📦 Tech Stack

**Backend:**
- Python 3.11
- FastAPI 0.120
- LangGraph 0.2.34
- SQLAlchemy 2.0.36 + Alembic 1.14
- PostgreSQL 15
- Pydantic v2
- JWT (python-jose), bcrypt (passlib)
- Redis + SlowAPI (rate limiting)
- Playwright + Lighthouse (quality checks)

**Frontend:**
- Next.js 16
- React 19
- TypeScript 5
- Axios, React Query

**Infrastructure:**
- Docker & Docker Compose
- Alembic (migrations)

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### 1. Clone Repository
```bash
git clone <repository-url>
cd Delivery-Pipeline
```

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env if needed (optional: add OPENAI_API_KEY, BACKEND_URL, webhooks)
```

Recommended local values:
```
BACKEND_URL=http://localhost:8000
CHAT_LOG_WEBHOOK_URL=
CHAT_LOG_WEBHOOK_SECRET=
```

### 3. Start with Docker Compose
```bash
docker compose up --build
```

This will:
- Start PostgreSQL database
- Run database migrations
- Start FastAPI backend on http://localhost:8000
- Start Next.js frontend on http://localhost:3000

### 4. Seed users (optional)
The backend **seeds all demo users on startup** (see Login section for the list; password `Admin@123`). If you need to re-run seeds:

```bash
# Seed all roles (resets passwords to Admin@123 for listed users)
docker compose exec backend python scripts/seed_users.py

# Or admin only
docker compose exec backend python scripts/seed_admin.py
```

### 5. Login
Open http://localhost:3000/login (or your Render frontend URL).

**Seed users (password for all: `Admin@123`)** — seeded on backend startup (localhost and Render):

| Role | Email | Password |
|------|--------|----------|
| **Admin** | subramaniyam.webdesigner@gmail.com | Admin@123 |
| **Consultant** | subramaniyam@consultant.com | Admin@123 |
| | jane@consultant.com | Admin@123 |
| **PC** | subramaniyam@pc.com | Admin@123 |
| | john@pc.com | Admin@123 |
| **Builder** | subramaniyam@builder.com | Admin@123 |
| | bob@builder.com | Admin@123 |
| **Tester** | subramaniyam@tester.com | Admin@123 |
| | alice@tester.com | Admin@123 |
| **Manager** | subramaniyam@manager.com | Admin@123 |
| | alice@manager.com | Admin@123 |
| | subramaniyam@usmanager.com | Admin@123 |
| **Sales** | subramaniyam@sales.com | Admin@123 |
| | alice@sales.com | Admin@123 |

## 🧪 End-to-end testing

### Start the full stack (local)

**PowerShell:**
```powershell
docker-compose up -d postgres redis backend frontend
```

**Bash:**
```bash
docker compose up -d postgres redis backend frontend
```

Wait ~30 seconds for the backend to run migrations, then:

| Service   | URL                      |
|----------|---------------------------|
| **App**  | http://localhost:3000     |
| **Login**| http://localhost:3000/login |
| **API docs** | http://localhost:8000/docs |
| **Health**   | http://localhost:8000/health |

### Seed users
The backend seeds all demo users (see table above) on **startup** (localhost and Render). To re-seed or reset passwords to `Admin@123`:

```powershell
docker-compose run --rm backend python scripts/seed_users.py
```

Or admin only: `docker-compose run --rm backend python scripts/seed_admin.py`

### Suggested E2E flow (manual)

1. **Login** – Open http://localhost:3000/login, sign in (e.g. Admin or use seeded user).
2. **Dashboard** – Confirm redirect to Dashboard; check “Your Focus” and breadcrumbs.
3. **Projects** – Go to Work → Projects; confirm list (or empty state).
4. **Create project** – As Sales/Admin: create a project, fill basics, save.
5. **Project detail** – Open a project; check stages (Sales Handoff first), tabs, and info.
6. **Roles** – As Admin: use DEV ONLY → Role to switch to Consultant/SALES; confirm nav and dashboard change; switch back.
7. **Other pages** – Visit Reports, Configuration (Admin), Users (Admin), Capacity, etc., as your role allows.

### Testing the AI agent workflow (not manual)

Stage work (Build, Test, Onboarding, etc.) runs via a **job queue** and a **background worker** that runs the AI/automation for each stage. To validate the agent workflow:

1. **Start the worker** (required for AI/automation to run):
   ```powershell
   docker-compose up -d postgres redis backend backend-worker frontend
   ```
   Or if the stack is already up: `docker-compose up -d backend-worker`

2. **Open a project** that is in a stage you can enqueue (e.g. Onboarding, Build, Test). On the project detail page, the **Job Queue** section shows the current stage and an **Enqueue** button for that stage.

3. **Enqueue a stage job** (this triggers the AI agent path):
   - Click **Enqueue Onboarding** / **Enqueue Build** / **Enqueue Test** (or the stage you are on).
   - The API enqueues a job; the **backend-worker** picks it up and runs the workflow (e.g. build agent, QA runner).

4. **Confirm the job ran**: The Job Queue table on the project page lists recent jobs and status (SUCCESS, RUNNING, FAILED). Refresh the project to see updated stage outputs or auto-advance to the next stage.

5. **Optional – watch worker logs**: `docker-compose logs -f backend-worker`

**Summary:** Use **Enqueue** to trigger the AI/agent workflow for a stage. The **backend-worker** must be running for jobs to execute. Manual actions (e.g. Advance, status updates) do not go through the agent.

**On Render:** Jobs will stay **Queued** until the **worker** service is running. In `render.yaml` the worker is `delivery-worker` (type: worker). Ensure it is deployed and running in your Render dashboard (same Redis and DB as the backend). If you only deploy the web backend and frontend, enqueued jobs will never run.

#### Render: Add the worker (step-by-step)

If your Render dashboard shows only `delivery-backend`, `delivery-frontend`, `delivery-db`, and `delivery-redis` (no worker), add the worker so Job Queue jobs can run:

1. **Option A – Deploy from blueprint (recommended)**  
   - In Render dashboard: **Projects** → your project (or **+ New** → **Blueprint**).  
   - Connect the repo if needed, then use **Apply** / **Deploy** from the blueprint that includes `render.yaml`.  
   - That will create/update all services in `render.yaml`, including **delivery-worker**.  
   - After deploy, in **Overview** you should see **delivery-worker** with status **Available** (or **Running**).

2. **Option B – Create the worker service by hand**  
   - **+ New** → **Background Worker**.  
   - **Connect repository**: same repo as backend (e.g. `subramaniyam22/Delivery-Pipeline`), branch `main`.  
   - **Name**: `delivery-worker` (so it matches the rest of the stack).  
   - **Region**: same as backend (e.g. Oregon).  
   - **Root Directory**: `backend`.  
   - **Runtime**: Python.  
   - **Build Command**:  
     `apt-get update && apt-get install -y nodejs npm git && npm install -g lighthouse && pip install -r requirements.txt && python -m playwright install --with-deps chromium`  
   - **Start Command**:  
     `python -m app.jobs.worker`  
   - **Environment**: Add the same env vars as the backend (required):  
     - `DATABASE_URL` → from **delivery-db** → **connectionString**  
     - `REDIS_URL` → from **delivery-redis** → **connectionString**  
     - `SECRET_KEY` → copy the value from **delivery-backend** (same secret so tokens match)  
     - `FRONTEND_URL` → your frontend URL (e.g. `https://delivery-frontend-liwm.onrender.com`)  
     - `AI_MODE` → `full`  
   - **Plan**: Starter (or same as backend if you prefer).  
   - **Create Background Worker**.  
   - After the first deploy, the worker will process enqueued jobs; Job Queue status should move from Queued to Running/Success.

   **Note:** The blueprint gives the worker its own generated `SECRET_KEY` (Render does not support copying env vars from another service). If your app requires the worker to use the same secret as the backend (e.g. for JWT), set `SECRET_KEY` on the **delivery-worker** service in the Render dashboard to the same value as **delivery-backend**.

3. **Backend/worker build failed (read-only file system)**  
   - Render's build environment does not allow `apt-get` or other system installs. The blueprint uses only `pip install -r requirements.txt` and `playwright install chromium`. Node/npm and Lighthouse are not installed on Render; QA features that need them may be limited unless you use a Docker-based deploy.

4. **Frontend deploy failed**  
   - Fix any build errors (e.g. TypeScript) and push to `main`; Render will redeploy the frontend.  
   - If the frontend service uses a different URL (e.g. `delivery-frontend-39z8.onrender.com`), set **NEXT_PUBLIC_API_URL** on the frontend to your backend URL. The backend blueprint sets **CORS_ORIGIN_REGEX** so any `https://*.onrender.com` origin is allowed; if you still see a login "Network Error" or CORS block, ensure the backend env has **CORS_ORIGIN_REGEX** = `^https://[a-zA-Z0-9-]+\.onrender\.com$` (or add your frontend URL to **CORS_ORIGINS**).

### Stop services

```powershell
docker-compose down
```

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

**Authentication:**
- `POST /auth/login` - Login with email/password

**Projects:**
- `POST /projects` - Create project (Sales/Consultant/Admin/Manager)
- `GET /projects` - List all projects
- `GET /projects/{id}` - Get project details
- `POST /projects/{id}/onboarding/update` - Update onboarding (Consultant/Admin/Manager)
- `POST /projects/{id}/assignment/publish` - Publish assignment (PC/Admin/Manager)
- `POST /projects/{id}/build/status` - Update build status (Builder/Admin/Manager)
- `POST /projects/{id}/test/status` - Update test status (Tester/Admin/Manager)

**Workflow:**
- `POST /projects/{id}/advance` - Advance workflow (Admin/Manager)
- `POST /projects/{id}/human/approve-build` - Approve build HITL (Admin/Manager)
- `POST /projects/{id}/human/send-back` - Send back to previous stage (Admin/Manager)

**AI Consultant & Webhooks:**
- `POST /api/ai/consult` - AI consultant chat
- `GET /api/ai/chat-logs/{project_id}` - Fetch chat logs
- `POST /api/ai/chat/send` - Send consultant message
- `POST /api/webhooks/chat-logs` - Receive chat log webhook

**Artifacts:**
- `POST /projects/{id}/artifacts/upload` - Upload artifact (role-based)
- `GET /projects/{id}/artifacts` - List artifacts

**Tasks:**
- `POST /projects/{id}/tasks` - Create task (PC/Admin/Manager)
- `GET /projects/{id}/tasks` - List tasks
- `PUT /tasks/{id}` - Update task

**Defects:**
- `POST /projects/{id}/defects/create-draft` - Create defect (Tester/Admin/Manager)
- `POST /projects/{id}/defects/validate` - Validate defect (Admin/Manager)

**Admin:**
- `POST /users` - Create user (Admin/Manager)
- `GET /users` - List users (Admin/Manager)
- `GET /admin/config` - List config (Admin/Manager)
- `PUT /admin/config/{key}` - Update config (Admin/Manager)

**Templates (AI + Git):**
- `GET /api/templates` - List templates (Admin/Manager)
- `POST /api/templates` - Create template
- `GET /api/templates/{id}` - Template detail
- `PUT /api/templates/{id}` - Update template (publish/unpublish)
- `POST /api/templates/{id}/generate-preview` - Generate AI preview
- `GET /previews/{template_id}/index.html` - Generated preview asset

## 🔧 Local Development (without Docker)

### Backend
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database (ensure PostgreSQL is running)
createdb delivery_db

# Run migrations (includes Template Registry extended fields: k5e6f7a8b9c0)
alembic upgrade head
# Or from backend folder: .\run_migration.bat (Windows) or ./run_migration.sh (Unix)

# Create admin user
python scripts/seed_admin.py

# Start server
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## 🗄️ Database Schema

**Users** - User accounts with roles
**Projects** - Project metadata, locations (`location_names`), and current stage
**Stage History** - Stage transition log (`stage_history`)
**Tasks** - Task assignments per stage
**StageOutputs** - Workflow stage execution results
**Artifacts** - File uploads per stage
**Defects** - Defect tracking
**AdminConfig** - Configuration templates and prompts
**AuditLogs** - Audit trail of all actions

## 🤖 LangGraph Workflow

The workflow uses LangGraph for orchestration with 6 nodes:

1. **onboarding_node** - Validates onboarding completeness
2. **assignment_node** - Creates task assignment plan
3. **build_hitl_node** - Human-in-the-loop for build approval
4. **test_node** - Analyzes test results
5. **defect_validation_node** - Validates defects and determines next action
6. **complete_node** - Generates project summary

Stage nodes delegate to dedicated agent classes in `backend/app/agents/` (onboarding, assignment, build, completion), with QA/Defect agents used in the Test/Defect Validation stages.

### Workflow Transitions
- onboarding → assignment → build → test
- test (with defects) → defect_validation
- defect_validation → build (if valid defects) OR test (if retest) OR complete
- human approval gates can be enabled per stage (HITL)

### LLM Integration
- Uses OpenAI GPT-4 if `OPENAI_API_KEY` is provided
- Falls back to **FakeLLM** (deterministic mock) if no API key
- All workflow logic works without external LLM dependencies

## 🔌 Connector Stubs

Located in `backend/app/agents/tools.py`:
- `fetch_requirement()` - External requirements system
- `fetch_external_task()` - Project management tool (Jira, etc.)
- `fetch_staging_url()` - Deployment system
- `fetch_defect_from_tracker()` - Defect tracker
- `fetch_logs()` - Logging infrastructure

Replace with actual API calls in production.

## 🔔 Webhooks

Chat logs can be delivered to an external system via webhook:

- `CHAT_LOG_WEBHOOK_URL` (optional) points to a receiver endpoint
- If not set, the service falls back to `BACKEND_URL + /api/webhooks/chat-logs`
- `CHAT_LOG_WEBHOOK_SECRET` (optional) is validated via the `X-Webhook-Secret` header

## 📝 Configuration Management

Admin/Manager can edit workflow configurations via UI or API:

**Config Keys:**
- `onboarding_template` - Onboarding form fields
- `assignment_template` - Assignment plan template
- `build_checklist_template` - Build checklist items
- `test_checklist_template` - Test checklist items
- `defect_validation_rules` - Defect validation rules
- `prompts` - LLM prompts per stage
- `global_stage_gates_json` - HITL gates per stage
- `global_thresholds_json` - Quality thresholds per stage
- `preview_strategy` - Preview artifact strategy
- `default_template_id` - Default template for builds

## 🧩 Template Registry (AI + Git)

Templates now support two source types:
- **AI**: intent-driven, no repo required, preview generated by the system.
- **Git**: repo + branch with preview link fallback to GitHub.

Template fields:
- `source_type` (`ai` | `git`)
- `intent`, `description`, `features_json`
- `preview_status` (`not_generated` | `generating` | `ready` | `failed`)
- `preview_url`, `preview_thumbnail_url`, `preview_last_generated_at`, `preview_error`

Preview generation:
- POST `/api/templates/{id}/generate-preview` generates a static HTML preview.
- Served from `/previews/{template_id}/index.html`.

## 🧪 Testing

### Test Authentication
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"subramaniyam.webdesigner@gmail.com","password":"Admin@123"}'
```

### Test RBAC
```bash
# Try accessing admin endpoint with different roles
curl -X GET http://localhost:8000/users \
  -H "Authorization: Bearer <token>"
```

### Test Workflow
1. Create project as Consultant
2. Upload onboarding artifacts
3. Assign tasks as PC
4. Update build status as Builder
5. Approve build as Admin
6. Run tests as Tester
7. Create defect drafts
8. Validate defects as Admin

### Migration Heads Note
This repo can have multiple Alembic heads in development. Use `alembic upgrade heads` locally. Before production deploys, merge heads and deploy with `alembic upgrade head`.

### Post-fix smoke tests
1) WebSocket notifications: Chrome DevTools → Network → WS → `/ws/notifications/{userId}` shows `?token=` in the URL.
2) Debug endpoints (prod mode): `curl -i https://<host>/debug-db` and `curl -i https://<host>/debug-schema` return 404.
3) Debug delete (prod mode): `curl -i -X DELETE "https://<host>/debug-projects?secret=clean_render_db_now"` returns 404.
4) Pydantic warning: log line `Valid config keys have changed in V2: * 'orm_mode' ...` should not appear.
5) Alembic migration command: confirm `render.yaml` uses `alembic upgrade head`.

## 🐛 Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker compose ps

# View logs
docker compose logs postgres

# Recreate database
docker compose down -v
docker compose up --build
```

### Migration Issues
```bash
# Reset migrations
docker compose exec backend alembic downgrade base
docker compose exec backend alembic upgrade heads
```

### Frontend API Connection
- Ensure `NEXT_PUBLIC_API_URL` points to backend
- Check CORS settings in `backend/app/config.py`

## 📂 Project Structure

```
Delivery-Pipeline/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Settings
│   │   ├── db.py                # Database session
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── auth.py              # JWT authentication
│   │   ├── rbac.py              # Role-based access control
│   │   ├── deps.py              # FastAPI dependencies
│   │   ├── routers/             # API routers
│   │   ├── services/            # Business logic
│   │   └── agents/              # LangGraph workflow
│   ├── alembic/                 # Database migrations
│   ├── generated_previews/      # AI template preview artifacts
│   ├── scripts/                 # Utility scripts
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # React components
│   │   └── lib/                 # Utilities (API, auth, RBAC)
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🌐 Render Environment Variables

The blueprint (`render.yaml`) sets DATABASE_URL, REDIS_URL, SECRET_KEY, CORS, FRONTEND_URL, and NEXT_PUBLIC_API_URL. After deploy, add or override in the **Render Dashboard** (each service → Environment):

| Variable | Where to get it |
|----------|------------------|
| **NEXT_PUBLIC_API_URL** (Frontend) | Your backend URL: Dashboard → delivery-backend → **URL** (e.g. `https://delivery-backend.onrender.com`) |
| **FRONTEND_URL**, **CORS_ORIGINS** (Backend) | Your frontend URL: Dashboard → delivery-frontend → **URL** |
| **BACKEND_URL** (Backend) | Same as backend URL (preview links, webhooks) |
| **OPENAI_API_KEY** | [OpenAI API Keys](https://platform.openai.com/api-keys) — for AI workflow and consultant |
| **RESEND_API_KEY** | [Resend](https://resend.com) — for onboarding/completion emails |
| **SENTRY_DSN** | [Sentry](https://sentry.io) — for error tracking |

Full list and optional vars (SMTP, S3, webhooks): see **[docs/RENDER_ENV.md](docs/RENDER_ENV.md)**.

## 🔒 Security Notes

- JWT tokens expire after 6 hours
- Passwords hashed with bcrypt
- RBAC enforced on every endpoint
- File upload size limited to 10MB
- SQL injection protection via SQLAlchemy ORM
- CORS configured for frontend origin only

## 📄 License

MIT License

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📞 Support

For issues and questions, please create a GitHub issue.
