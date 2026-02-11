# Render Environment Variables

Set these in the **Render Dashboard** for each service (Environment tab). The blueprint (`render.yaml`) already provides some; add or override as below.

---

## Already set by Blueprint

| Variable | Service(s) | Source |
|----------|------------|--------|
| `DATABASE_URL` | Backend, Worker | From **delivery-db** (Internal Connection String) |
| `REDIS_URL` | Backend, Worker | From **delivery-redis** (Connection String) |
| `SECRET_KEY` | Backend, Worker | **Generate** (Render generates a random value) |
| `CORS_ORIGINS`, `CORS_ORIGIN_REGEX` | Backend | Fixed in blueprint |
| `FRONTEND_URL` | Backend, Worker | Fixed in blueprint |
| `PYTHON_VERSION`, `AI_MODE`, `RATE_LIMIT_*` | Backend | Fixed in blueprint |
| `NODE_VERSION` | Frontend | Fixed in blueprint |
| `NEXT_PUBLIC_API_URL` | Frontend | Set in blueprint to backend URL; **override** if your backend URL differs |

---

## Add or override in Dashboard

### Required (set after first deploy)

| Variable | Service | Where to get it | Example |
|----------|---------|------------------|---------|
| **NEXT_PUBLIC_API_URL** | **delivery-frontend** | Backend service URL from Render: Backend → **URL** (e.g. `https://delivery-backend.onrender.com`) | `https://delivery-backend.onrender.com` |
| **FRONTEND_URL** | **delivery-backend**, **delivery-worker** | Frontend service URL from Render: Frontend → **URL** | `https://delivery-frontend.onrender.com` |
| **CORS_ORIGINS** | **delivery-backend** | Same as FRONTEND_URL; if you have multiple frontends, comma-separate | `https://delivery-frontend.onrender.com` |
| **BACKEND_URL** | **delivery-backend** | Same as backend URL (for preview links, webhooks) | `https://delivery-backend.onrender.com` |

### Optional (for full functionality)

| Variable | Service | Where to get it |
|----------|---------|------------------|
| **OPENAI_API_KEY** | Backend, Worker | [OpenAI API Keys](https://platform.openai.com/api-keys) — required for AI workflow, onboarding agent, AI consultant |
| **RESEND_API_KEY** | Backend | [Resend](https://resend.com) → API Keys — for transactional email (onboarding links, completion emails) |
| **SENTRY_DSN** | Backend | [Sentry](https://sentry.io) → Project → Client Keys (DSN) — for error tracking |
| **ENVIRONMENT** | Backend, Worker | Set to `production` for production behavior (cookie security, etc.); blueprint sets this |

### Optional (email – if not using Resend)

| Variable | Service | Where to get it |
|----------|---------|------------------|
| SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, FROM_EMAIL | Backend | Your SMTP provider (Gmail, SendGrid, etc.) |

### Optional (storage – if using S3 instead of local)

| Variable | Service | Where to get it |
|----------|---------|------------------|
| STORAGE_BACKEND | Backend, Worker | Set to `s3` |
| S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY, S3_REGION | Backend, Worker | AWS IAM / S3 or compatible (e.g. Cloudflare R2) |
| S3_PUBLIC_BASE_URL or STORAGE_PUBLIC_BASE_URL | Backend | Public URL for uploaded files |

### Optional (webhooks)

| Variable | Service | Where to get it |
|----------|---------|------------------|
| CHAT_LOG_WEBHOOK_URL | Backend | Your webhook endpoint URL |
| CHAT_LOG_WEBHOOK_SECRET | Backend | Secret you define for validating webhook payloads |

---

## Quick checklist after deploy

1. **Backend** → Environment: set **BACKEND_URL** = your backend URL; **FRONTEND_URL** = your frontend URL; **ENVIRONMENT** = `production`; optionally **OPENAI_API_KEY**, **RESEND_API_KEY**, **SENTRY_DSN**.
2. **Frontend** → Environment: set **NEXT_PUBLIC_API_URL** = your backend URL (must match backend).
3. **Worker** → Environment: same **SECRET_KEY** as backend (copy from Backend env); **FRONTEND_URL** = frontend URL; optionally **OPENAI_API_KEY**.
4. Redeploy each service after changing env vars (or use **Manual Deploy**).
