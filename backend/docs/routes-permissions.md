# API routes and permissions

This document summarizes which **role(s)** can access which API areas. It is derived from `app/rbac.py` and the route dependencies in `app/routers/*`.

## Role summary (from `rbac.py`)

| Role        | full_access | manage_config | approve_workflow | all_stages | Notes                          |
|------------|-------------|---------------|------------------|------------|--------------------------------|
| ADMIN      | ✓           | ✓             | ✓                | ✓          | Full access                    |
| MANAGER    | ✓           | ✓             | ✓                | ✓          | Full access                    |
| CONSULTANT | —           | —             | —                | —          | ONBOARDING, update_onboarding  |
| PC         | —           | —             | —                | —          | ASSIGNMENT, manage_assignment  |
| BUILDER    | —           | —             | —                | —          | BUILD only                     |
| TESTER     | —           | —             | —                | —          | TEST, create_defects           |
| SALES      | —           | —             | —                | —          | SALES, ONBOARDING, view_all    |

## Routes requiring Admin or Manager only

These endpoints use `check_full_access(current_user.role)` or `require_admin_manager` / `get_admin_or_manager_dependency()`:

| Area           | Path pattern / description |
|----------------|----------------------------|
| **Workflow**   | `POST /projects/{id}/advance`, `POST /projects/{id}/human/approve-build`, `POST /projects/{id}/human/send-back` |
| **Jobs**       | `POST /projects/{id}/stages/{stage}/enqueue` (manual enqueue is recovery-only; autopilot is primary) |
| **Config**     | `GET/PUT /admin/config/{key}` (Admin Config CRUD) |
| **Pipeline**   | `POST /projects/{id}/pipeline/pause`, `POST /projects/{id}/pipeline/resume`, enqueue-related actions |
| **Projects**   | `GET /projects/{id}/phase-summary`, `POST /projects/{id}/complete/close`, `POST /projects/{id}/hitl-toggle`, `POST /projects/{id}/confirm-fallback` (and other phase/gate controls) |
| **Onboarding** | Create/delete project-tasks, send reminder (some paths) |
| **SLA**        | Update SLA configurations (admin-only branch) |
| **Metrics**    | `GET /admin/metrics/*` |
| **Debug**      | `GET /api/debug/chrome-path` |

## Routes with no auth (public or token-based)

| Area              | Path pattern | Notes |
|-------------------|--------------|--------|
| **Client onboarding** | `GET/PUT /projects/client-onboarding/{token}`, `POST .../submit`, `POST .../upload-logo`, etc. | Access by signed token in URL; no login |
| **Preview**       | `GET /public/preview/{token}` | Signed token |
| **Sentiment**     | `POST /public/sentiment/*` | Public submit |
| **Health**        | `GET /healthz`, `GET /readyz` | No auth |
| **Version**       | `GET /version` | No auth |

## All other routes

- **Authenticated** (any valid user with a role): require `get_current_active_user` or `get_current_user`. Project- and stage-specific access is then enforced in the handler via `check_full_access`, `can_access_stage`, or resource-level checks (e.g. only assigned builder can update build status).

## Generating the full route list

From the repo root:

```bash
cd backend && python -m scripts.list_routes
```

Or with coverage disabled:

```bash
cd backend && python scripts/list_routes.py
```

Use the output to spot new endpoints when adding features; then update this doc and the "Routes requiring Admin or Manager only" section as needed.
