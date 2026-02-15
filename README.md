# Delivery Automation Suite MVP

Production-ready MVP with **FastAPI + LangGraph** backend, **Next.js (App Router)** frontend, and strict **role-based access control (RBAC)**.

## 🎯 Overview

A multi-agent workflow system with **7 stages** plus AI template management:

1. **Sales Handover** - Project creation, drafts, and handover to delivery
2. **Onboarding** - Initial project setup, client data, and documentation (auto-reminder optional)
3. **Assignment** - Task assignment and resource allocation
4. **Build** - Development work (Human-in-the-loop optional)
5. **Test** - Quality assurance and testing
6. **Defect Validation** - Defect analysis and validation
7. **Complete** - Project closure and summary

Key capabilities:
- **Reports** (Insights): Executive dashboard with **Projects Delivered** (count of projects in Complete status only; not active pipeline count), cycle time, SLA breaches, client sentiment; Insights with delivery health, client insights, quality & defects; filters by date range, client, stage, template; Export CSV/PDF
- **Client Management** (Consultant+): Track client contacts, project context, pending requirements, last reminder; update client emails; send reminder emails
- **Template Registry**: AI and Git templates; blueprint generation; **preview** (Static = fast/cached, Live = accurate/dynamic); **validation** (Lighthouse + Axe for responsiveness and accessibility); Performance and Evolution tabs; WCAG 2 AA–friendly preview renderer (contrast, main landmark, unique section labels)
- **Preview Strategy** (Admin): Choose Static Preview (fast, cached) or Live Preview (accurate, dynamic). **Image prompts** (optional) in Create Template guide AI for exterior/interior/lifestyle/people/neighborhood imagery
- AI-driven workflow orchestration with optional human approval gates (global and per-project)
- SLA configuration, quality thresholds, HITL gates, and Learning Proposals in admin UI
- Operations dashboard for job queue health, retries, and stuck runs; **Dashboard** template performance (top / needs improvement) with threshold note and deduplication by template name
- Quality dashboard and client sentiment tracking
- Auto-advance from Sales to Onboarding when required fields are complete; **onboarding auto-reminder** toggle persists when navigating away
- Multi-location support (`location_names`) and stage timeline history (`stage_history`)
- Notifications, audit logs, and admin configuration UI; **toasts and info banner** have close buttons
- Chat log webhooks for external systems and training pipelines
- JWT-secured notification WebSocket connections
- Template preview iframe: auth via `?access_token=` or trusted Referer; **CHROME_PATH** / **PLAYWRIGHT_BROWSERS_PATH** for validation (see Render and Validation sections)
- Debug endpoints gated in production; **GET /api/debug/chrome-path** (Admin/Manager) returns Chrome path for Render env

## 🔐 Roles & Permissions

| Role | Permissions |
|------|-------------|
| **Admin** | Full access to all endpoints and UI; System Configuration (templates, SLA, thresholds, Preview Strategy, HITL, Learning); debug/chrome-path |
| **Manager** | Same as Admin for workflow and config; Client Management; template publish/recommend |
| **Consultant** | Create projects, update onboarding, view status; **Client Management** (all projects for Admin/Manager; Consultant/PC see only assigned projects) |
| **PC (Project Coordinator)** | Task assignment access, manage assignment stage; Client Management for assigned projects |
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
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.2
OPENAI_TIMEOUT_SECONDS=60
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
   - That will create/update all services, including **delivery-worker** (Docker) and **delivery-backend** (Docker).  
   - After deploy, **delivery-worker** should show status **Available** (or **Running**).

2. **Option B – Create the worker by hand (use Docker)**  
   - **+ New** → **Background Worker**.  
   - **Connect repository**: same repo, branch `main`.  
   - **Name**: `delivery-worker`. **Region**: same as backend.  
   - **Runtime**: **Docker**. **Dockerfile path**: `worker/Dockerfile`. **Docker build context**: `.` (root).  
   - **Build command** / **Start command**: leave empty (Dockerfile defines them).  
   - **Environment**: Same as backend (DATABASE_URL, REDIS_URL, SECRET_KEY, FRONTEND_URL, BACKEND_URL, AI_MODE, etc.). Copy from **delivery-backend**; set **SECRET_KEY** to the same value as the backend so JWT matches.  
   - **Create Background Worker**.

   **Note:** If you create the backend or worker as **native Python** instead of Docker, Lighthouse and Playwright will not be available and template validation will fail. Use **Docker** for both.

3. **Frontend deploy failed**  
   - Fix any build errors (e.g. TypeScript) and push to `main`; Render will redeploy the frontend.  
   - Set **NEXT_PUBLIC_API_URL** on the frontend to your backend URL. The backend sets **CORS_ORIGIN_REGEX** so `https://*.onrender.com` is allowed; if you see a login "Network Error" or CORS block, add your frontend URL to **CORS_ORIGINS** or ensure **CORS_ORIGIN_REGEX** matches.

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
- `GET /api/templates/{id}/preview`, `GET /api/templates/{id}/preview/{path}` - Preview proxy (auth: Bearer or `?access_token=` or trusted Referer)
- `GET /api/debug/chrome-path` - Return Chrome path for Lighthouse (Admin/Manager only)

**Client Management (Consultant+):**
- `GET /client-management/projects` - List projects with client info, pending requirements, last reminder
- `PUT /client-management/projects/{id}/client-emails` - Update client emails/contact
- `POST /client-management/send-reminder` - Send reminder email to client
- `GET /client-management/reminders/{project_id}` - Reminder history
- `GET /client-management/pending-requirements/{project_id}` - Pending requirements for project

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

**Users** – User accounts with roles  
**Projects** – Project metadata, locations (`location_names`), current stage, client fields (`client_name`, `client_company`, `client_primary_contact`, `client_emails`), client preview and stage history  
**OnboardingData** – Per-project onboarding (contacts_json, requirements_json, copy_text, theme, auto_reminder_enabled, etc.)  
**Stage History** – Stage transition log (`stage_history`)  
**ClientReminderLog** – Sent reminders (project_id, reminder_type, sent_to, subject, message, sent_at)  
**Tasks** – Task assignments per stage  
**StageOutputs** – Workflow stage execution results  
**Artifacts** – File uploads per stage  
**Defects** – Defect tracking  
**TemplateRegistry** – Templates with blueprint_json, preview_status, validation_status, validation_last_run_at, result_json, performance_metrics_json  
**TemplateValidationJob** – Validation job queue and results  
**AdminConfig** – Configuration (templates, SLA, thresholds, preview_strategy, HITL gates)  
**AuditLogs** – Audit trail of all actions  
**Executive / Reports** – Aggregates: `projects_delivered` (count of COMPLETED), total_projects, cycle time, SLA breaches, sentiment (from SLA/analytics endpoints)

## 🤖 LangGraph Workflow & Pipeline Stages

The workflow uses LangGraph for orchestration. **Pipeline stages** (in order): Sales Handover → Onboarding → Assignment → Build → Test → Defect Validation → Complete.

**Nodes:** onboarding_node, assignment_node, build_hitl_node, test_node, defect_validation_node, complete_node. Stage nodes delegate to dedicated agent classes in `backend/app/agents/` (onboarding, assignment, build, completion), with QA/Defect agents used in Test and Defect Validation.

### Workflow Transitions
- Sales Handover: drafts and handover; activate project to move to Onboarding
- Onboarding → Assignment → Build → Test (with optional HITL at Build)
- Test (with defects) → Defect Validation
- Defect Validation → Build (valid defects) OR Test (retest) OR Complete
- Human approval gates can be enabled per stage (HITL) via System Configuration → HITL Gates

### LLM Integration
- Uses OpenAI (model from **OPENAI_MODEL**, default `gpt-4o`) if `OPENAI_API_KEY` is provided
- Falls back to **FakeLLM** (deterministic mock) if no API key
- All workflow logic works without external LLM dependencies
- **If blueprint generation fails**, first verify `OPENAI_MODEL` is set (use `gpt-4o`).

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

Templates support two source types:
- **AI**: intent-driven, no repo required; preview and blueprint generated by the system.
- **Git**: repo + branch with preview link fallback to GitHub.

**Template fields:** `source_type` (`ai` | `git`), `intent`, `description`, `features_json`, `preview_status` (`not_generated` | `generating` | `ready` | `failed`), `preview_url`, `preview_thumbnail_url`, `preview_last_generated_at`, `preview_error`, `validation_status`, `validation_last_run_at`, `performance_metrics_json`.

**Create Template wizard:** Name, description, category, style, industry, feature tags; **Image prompts (optional)** for Exterior, Interior, Lifestyle, People, Neighborhood — short descriptions that guide AI when generating or selecting images for the template. Leave blank to skip.

**Preview Strategy (Admin, System Configuration):**
- **Static Preview (fast, cached)** – Pre-builds HTML and serves from cache; best for quick checks.
- **Live Preview (accurate, dynamic)** – Builds in a production-like environment; slower but closer to final site.

**Preview in UI:** Preview tab loads the template in an iframe. Auth: `?access_token=` in the URL or trusted Referer for subresources. Backend sets `Content-Security-Policy: frame-ancestors *` and omits `X-Frame-Options` for `/api/templates/.../preview` so the frontend can embed it.

**Validation (Lighthouse + Axe):** Run Validation uses Lighthouse (mobile viewport, performance/accessibility/SEO) and Axe (accessibility). Requires **Chrome/Chromium** in the backend environment (see **Template validation on Render** below). Copy and SEO validation run separately. **Fix Blueprint** opens suggestions when validation fails (e.g. install Lighthouse/Playwright).

**Preview renderer (WCAG 2 AA):** Generated preview HTML uses contrast-safe text on primary/accent/white, one `<main>` landmark, and unique `aria-label`s per section so Axe color-contrast and landmark rules pass.

**Endpoints:** POST `/api/templates/{id}/generate-preview`, GET `/api/templates/{id}/preview` and `/api/templates/{id}/preview/{path}` (auth: Bearer or `?access_token=` or trusted Referer), GET `/api/debug/chrome-path` (Admin/Manager – returns `CHROME_PATH` for Render).

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

### Template validation: "Chrome/Chromium not found" or "CHROME_PATH must be set"
- **Backend must use Docker** (not native Python). In Render, set the backend to **Runtime: Docker**, **Dockerfile path:** `backend/Dockerfile`, **Docker context:** `backend`; leave Build/Start command empty.
- Get the Chrome path: as Admin, open `GET /api/debug/chrome-path`, or in Render Shell run `python scripts/print_chrome_path.py` from the backend directory.
- Add **CHROME_PATH** in the backend Environment to that path; save and redeploy.

### Client Management: "500" or "Unable to load projects"
- The `/client-management/projects` endpoint reads onboarding data (e.g. `requirements_json`, `contacts_json`). If you see 500, ensure the backend is up to date (fixed in code to use correct OnboardingData fields). Redeploy the backend.

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
│   │   ├── deps.py              # FastAPI dependencies (incl. get_current_user_for_preview)
│   │   ├── routers/             # API routers (auth, projects, configuration, client_management, etc.)
│   │   ├── services/            # Business logic (preview_renderer, validation_runner, storage, etc.)
│   │   ├── agents/              # LangGraph workflow
│   │   └── middleware/          # Security headers (X-Frame-Options, CSP for preview)
│   ├── alembic/                 # Database migrations
│   ├── generated_previews/      # AI template preview artifacts (optional)
│   ├── scripts/
│   │   ├── print_chrome_path.py # Print CHROME_PATH for Render (run in Shell)
│   │   ├── seed_admin.py
│   │   └── seed_users.py
│   ├── requirements.txt
│   └── Dockerfile               # Node + Lighthouse + Playwright chromium/headless_shell
├── worker/
│   └── Dockerfile               # Background worker (Lighthouse, Playwright, Chromium)
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   ├── components/          # React components
│   │   └── lib/                # Utilities (API, auth, RBAC)
│   ├── package.json
│   └── (no Dockerfile; Render uses Node runtime)
├── render.yaml                  # Render Blueprint (backend, frontend, worker, redis, db)
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🌐 Render Deployment

**Blueprint (`render.yaml`):** Defines `delivery-backend` (Docker), `delivery-frontend` (Node), `delivery-worker` (Docker), `delivery-redis`, `delivery-db`. Use **Blueprint** → Apply so the backend uses **Docker** (required for template validation).

**Backend (template validation):** The backend must run as **Docker** (not native Python) so Lighthouse and Playwright are installed in the image. When using Docker:
- **Build command** and **Start command** in Render are left **empty** (Dockerfile defines build and CMD).
- **Dockerfile path:** `backend/Dockerfile`; **Docker context:** `backend`.
- Env **PLAYWRIGHT_BROWSERS_PATH** = `/app/.cache/ms-playwright` is set in the blueprint.

If validation fails with "Chrome/Chromium not found" or "CHROME_PATH must be set":
1. **Get the path:** Log in as Admin and open `GET /api/debug/chrome-path` (e.g. `https://<backend-url>/api/debug/chrome-path`), or in Render Shell run `python scripts/print_chrome_path.py` from the backend directory.
2. **Set env:** Backend → Environment → Add **CHROME_PATH** = the value returned (e.g. `/app/.cache/ms-playwright/chromium-1208/chrome-linux/chrome`).
3. Save and redeploy.

**Worker:** Uses `worker/Dockerfile`; has Lighthouse, Playwright, and Chromium for jobs that need them. Same Redis and DB as backend.

## 🌐 Render Environment Variables

The blueprint sets DATABASE_URL, REDIS_URL, SECRET_KEY, CORS, FRONTEND_URL, BACKEND_URL, PLAYWRIGHT_BROWSERS_PATH (backend), and NEXT_PUBLIC_API_URL (frontend). After deploy, add or override in the **Render Dashboard** (each service → Environment):

| Variable | Where to get it |
|----------|------------------|
| **NEXT_PUBLIC_API_URL** (Frontend) | Your backend URL: Dashboard → delivery-backend → **URL** (e.g. `https://delivery-backend.onrender.com`) |
| **FRONTEND_URL**, **CORS_ORIGINS** (Backend) | Your frontend URL: Dashboard → delivery-frontend → **URL** |
| **BACKEND_URL** (Backend) | Same as backend URL (preview links, webhooks) |
| **OPENAI_API_KEY** | [OpenAI API Keys](https://platform.openai.com/api-keys) — for AI workflow and consultant |
| **OPENAI_MODEL** | Use `gpt-4o` only (default in code). Set in env to override. |
| **OPENAI_TEMPERATURE** | 0.0–1.0 (default: `0.2`). Lower = more deterministic. |
| **OPENAI_MAX_TOKENS** | Optional. Leave unset for library default. |
| **OPENAI_TIMEOUT_SECONDS** | Request timeout (default: `60`). |
| **RESEND_API_KEY** | [Resend](https://resend.com) — for onboarding/completion emails |
| **SENTRY_DSN** | [Sentry](https://sentry.io) — for error tracking |
| **PLAYWRIGHT_BROWSERS_PATH** (Backend) | Set by blueprint to `/app/.cache/ms-playwright`. Do not override unless needed. |
| **CHROME_PATH** (Backend, optional) | If template validation reports "Chrome/Chromium not found", set to the path from `GET /api/debug/chrome-path` or `python scripts/print_chrome_path.py`. |
| **AWS S3** (optional) | Set **STORAGE_BACKEND=s3** and **S3_BUCKET**, **S3_ACCESS_KEY**, **S3_SECRET_KEY**, **S3_REGION** from [AWS IAM](https://console.aws.amazon.com/iam/) / S3 or Cloudflare R2. See [docs/RENDER_ENV.md](docs/RENDER_ENV.md#optional-aws-s3-or-s3-compatible-storage). |

Full list and optional vars (SMTP, webhooks): see **[docs/RENDER_ENV.md](docs/RENDER_ENV.md)**.

### Verifying OpenAI at runtime
- **Active model**: On startup, the backend logs `AI_MODE` and `OPENAI_MODEL`. Check container logs (e.g. `docker compose logs backend`) to confirm which model is in use.
- **Test AI consultant**: `POST /api/ai/consult` with a JSON body `{"message": "Hello", "project_id": "<uuid>"}` (and optional `context`). Use the API docs at `http://localhost:8000/docs` or curl. If `OPENAI_API_KEY` is missing and AI is enabled, the endpoint returns **503** with a clear message.

### Debugging blueprint generation
- **Status**: `GET /api/templates/{template_id}/blueprint/status` returns `blueprint_status` (idle | queued | generating | validating | ready | failed) and `latest_run` (run_id, status, error_message, model_used). Poll every 3s until ready/failed.
- **Run details** (Admin/Manager): `GET /api/blueprint-runs/{run_id}` returns full run including `error_code`, `error_details`, `raw_output` (redacted). Use when a run fails to inspect validation errors or LLM output.
- **Worker health**: `GET /system/health` returns `worker_healthy` (true if heartbeat &lt; 60s). If false, blueprint jobs will not execute; ensure the backend (or worker process) is running and Redis is reachable.
- **Logs**: Worker logs include `correlation_id` for each run; search logs by that id to trace a specific blueprint generation.

## 🔒 Security Notes

- JWT tokens expire after 6 hours
- Passwords hashed with bcrypt
- RBAC enforced on every endpoint
- File upload size limited to 10MB
- SQL injection protection via SQLAlchemy ORM
- CORS configured for frontend origin only

## 📄 License

Not Licensed

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📞 Support

TBD
