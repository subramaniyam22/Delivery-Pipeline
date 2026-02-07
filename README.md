# Multi-Agent Delivery Pipeline MVP

Production-ready MVP with **FastAPI + LangGraph** backend, **Next.js** frontend, and strict **role-based access control (RBAC)**.

## 🎯 Overview

A multi-agent workflow system with 6 stages:
1. **Project Onboarding** - Initial project setup and documentation
2. **Project Assignment** - Task assignment and resource allocation
3. **Build** - Development work (Human-in-the-loop optional)
4. **Test** - Quality assurance and testing
5. **Defect Validation** - Defect analysis and validation
6. **Complete** - Project closure and summary

Key capabilities:
- AI-driven workflow orchestration with optional human approval gates
- Auto-advance from Sales to Onboarding when all required fields are complete
- Multi-location support (`location_names`) and stage timeline history (`stage_history`)
- Chat log webhooks for external systems and training pipelines

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
- **Next.js 14** with App Router
- **TypeScript** for type safety
- **Axios** for API communication
- **Role-based UI** rendering

## 📦 Tech Stack

**Backend:**
- Python 3.11
- FastAPI 0.109
- LangGraph 0.0.20
- SQLAlchemy 2.0
- PostgreSQL 15
- Pydantic v2
- JWT (python-jose)
- Bcrypt (passlib)

**Frontend:**
- Next.js 14
- React 18
- TypeScript 5
- Axios

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
docker-compose up --build
```

This will:
- Start PostgreSQL database
- Run database migrations
- Start FastAPI backend on http://localhost:8000
- Start Next.js frontend on http://localhost:3000

### 4. Create Admin User
```bash
# Option 1: Using seed script
docker-compose exec backend python scripts/seed_admin.py

# Option 2: Seed all default users/roles
docker-compose exec backend python scripts/seed_users.py

# Option 3: Using API endpoint (only works if no users exist)
curl -X POST http://localhost:8000/users/seed
```

### 5. Login
Open http://localhost:3000/login

**Default credentials:**
- Email: `subramaniyam.webdesigner@gmail.com`
- Password: `Admin@123`

⚠️ **Change password after first login!**

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

**Authentication:**
- `POST /auth/login` - Login with email/password

**Projects:**
- `POST /projects` - Create project (Consultant/Admin/Manager)
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

# Run migrations
alembic upgrade head

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

## 🧪 Testing

### Test Authentication
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@delivery.com","password":"admin123"}'
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

## 🐛 Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps

# View logs
docker-compose logs postgres

# Recreate database
docker-compose down -v
docker-compose up --build
```

### Migration Issues
```bash
# Reset migrations
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head
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
