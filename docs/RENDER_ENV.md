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
| **SENTRY_DSN** | Backend | [Sentry](https://sentry.io) → Backend project → Client Keys (DSN) — for error tracking |
| **NEXT_PUBLIC_SENTRY_DSN** | **delivery-frontend** | [Sentry](https://sentry.io) → Frontend project (Next.js) → Client Keys (DSN) — for client/server error tracking |
| **ENVIRONMENT** | Backend, Worker | Set to `production` for production behavior (cookie security, etc.); blueprint sets this |

### Optional (email – if not using Resend)

| Variable | Service | Where to get it |
|----------|---------|------------------|
| SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, FROM_EMAIL | Backend | Your SMTP provider (Gmail, SendGrid, etc.) |

### Optional (AWS S3 or S3-compatible storage)

Use S3 when you want uploads (artifacts, previews, etc.) to live in object storage instead of the server’s local disk (recommended on Render so files survive redeploys).

| Variable | Service | Where to get it |
|----------|---------|------------------|
| **STORAGE_BACKEND** | Backend, Worker | Set to `s3` to enable S3. Omit or `local` for disk storage. |
| **S3_BUCKET** | Backend, Worker | **AWS:** S3 → Create bucket / use existing → bucket name. **R2:** Cloudflare Dashboard → R2 → bucket name. |
| **S3_ACCESS_KEY** | Backend, Worker | **AWS:** IAM → Users → Create user (programmatic) → Attach policy (e.g. `AmazonS3FullAccess` or custom) → Create access key → copy **Access key ID**. **R2:** R2 → Manage R2 API Tokens → Create API token → copy **Access Key ID**. |
| **S3_SECRET_KEY** | Backend, Worker | **AWS:** Same flow as above → copy **Secret access key** (shown once). **R2:** Same API token → copy **Secret Access Key**. |
| **S3_REGION** | Backend, Worker | **AWS:** e.g. `us-east-1`, `eu-west-1` (bucket region). **R2:** Optional; use `auto` or leave empty if using endpoint. |
| **S3_ENDPOINT_URL** | Backend, Worker | Only for **non-AWS** S3-compatible storage. **Cloudflare R2:** `https://<account_id>.r2.cloudflarestorage.com`. **MinIO / DigitalOcean Spaces:** your endpoint URL. Leave empty for real AWS S3. |
| **S3_PUBLIC_BASE_URL** or **STORAGE_PUBLIC_BASE_URL** | Backend, Worker | Public base URL for generated file URLs (e.g. `https://your-bucket.s3.region.amazonaws.com`, or CloudFront `https://d123.cloudfront.net`, or R2 public bucket URL). If unset, the app may use signed/pre-signed URLs. |

#### Backend and Worker both need S3 vars

Set the same S3 environment variables on **both delivery-backend and delivery-worker**. The backend handles API uploads and serving files; the worker runs build/test/defect jobs and reads/writes artifacts. They must use the same bucket and credentials so uploaded and generated files are visible to both.

#### How to update S3 values in Render

1. Open [Render Dashboard](https://dashboard.render.com) → your project → **delivery-backend** and **delivery-worker**.
2. Go to the **Environment** tab.
3. Click **Add Environment Variable** (or edit an existing one) and add each variable below. Use **Key** = exact name, **Value** = the value you got from AWS or R2.
4. After saving, trigger a **Manual Deploy** (or push to your repo) so the service restarts with the new env.

| Variable | What to set in Render | Where to get the value |
|----------|------------------------|-------------------------|
| **STORAGE_BACKEND** | `s3` (to use S3). Use `local` or leave unset for server disk. | — |
| **S3_BUCKET** | Your bucket name. | **AWS:** [S3 Console](https://s3.console.aws.amazon.com/) → create or open bucket → use the bucket name (e.g. `my-app-uploads`). **R2:** Cloudflare Dashboard → R2 → your bucket → name. |
| **S3_ACCESS_KEY** | Access key ID (not the secret). | **AWS:** [IAM](https://console.aws.amazon.com/iam/) → Users → your user (or create one) → Security credentials → Create access key → choose “Application running outside AWS” → copy **Access key ID**. **R2:** R2 → Manage R2 API Tokens → Create API token → copy **Access Key ID**. |
| **S3_SECRET_KEY** | Secret access key. | **AWS:** From the same “Create access key” step → copy **Secret access key** (shown once; save it before closing). **R2:** Same API token → copy **Secret Access Key**. |
| **S3_REGION** | AWS region of the bucket. | **AWS:** In S3, bucket region (e.g. `us-east-1`, `eu-west-1`). **R2:** Can leave empty or set `auto` if you use **S3_ENDPOINT_URL**. |
| **S3_ENDPOINT_URL** | Only for non-AWS S3-compatible storage. | **AWS:** Leave **empty**. **R2:** `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` (ACCOUNT_ID in Cloudflare Dashboard → R2 → right-hand side). **MinIO/Spaces:** Your provider’s S3 endpoint URL. |
| **S3_PUBLIC_BASE_URL** or **STORAGE_PUBLIC_BASE_URL** | Optional. Base URL for public file links. | **AWS:** e.g. `https://your-bucket.s3.us-east-1.amazonaws.com`, or your CloudFront domain. **R2:** R2 public bucket URL or custom domain if configured. |

**Alternate names (app also accepts):**  
You can use **AWS_ACCESS_KEY_ID**, **AWS_SECRET_ACCESS_KEY**, **AWS_REGION**, and **AWS_S3_BUCKET** instead of **S3_ACCESS_KEY**, **S3_SECRET_KEY**, **S3_REGION**, and **S3_BUCKET** if you prefer.

**Backwards-compatible names** (app accepts either):  
`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` / `AWS_S3_BUCKET` work in place of `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_REGION` / `S3_BUCKET`.

**Quick AWS setup:** AWS Console → S3 (create bucket) → IAM → User with programmatic access and `AmazonS3FullAccess` (or a custom policy for that bucket) → create access key → paste into **S3_ACCESS_KEY** and **S3_SECRET_KEY** in Render.

### Optional (webhooks)

| Variable | Service | Where to get it |
|----------|---------|------------------|
| CHAT_LOG_WEBHOOK_URL | Backend | Your webhook endpoint URL |
| CHAT_LOG_WEBHOOK_SECRET | Backend | Secret you define for validating webhook payloads |

---

## Which env vars does the Worker need?

| Variable | Backend only | Worker too | Why |
|----------|--------------|------------|-----|
| **RESEND_API_KEY** | ✓ | ✓ | Worker sends completion and stage emails. |
| **OPENAI_API_KEY** | ✓ | ✓ | Worker runs Build (self-review), Test (QA/defect agents), and other stages that use the LLM. |
| **BACKEND_URL** | ✓ | ✓ | Worker uses it in site_builder for preview URLs. |
| **CORS_ORIGINS** | ✓ | No | Only the FastAPI web server uses CORS; worker does not serve HTTP. |
| **CORS_ORIGIN_REGEX** | ✓ | No | Same as above. |
| **SENTRY_DSN** | ✓ | Optional | Add to worker if you want worker errors in Sentry. |
| **S3_*** / **STORAGE_BACKEND** | ✓ | ✓ | Worker reads/writes artifacts; must use same bucket as backend. |

So: add **RESEND_API_KEY**, **OPENAI_API_KEY**, and **BACKEND_URL** to the worker as well. Do **not** add CORS_ORIGINS or CORS_ORIGIN_REGEX to the worker.

---

## Quick checklist after deploy

1. **Backend** → Environment: set **BACKEND_URL** = your backend URL; **FRONTEND_URL** = your frontend URL; **ENVIRONMENT** = `production`; optionally **OPENAI_API_KEY**, **RESEND_API_KEY**, **SENTRY_DSN**, S3 vars.
2. **Frontend** → Environment: set **NEXT_PUBLIC_API_URL** = your backend URL (must match backend).
3. **Worker** → Environment: same **SECRET_KEY** as backend; **FRONTEND_URL** = frontend URL; **BACKEND_URL** = backend URL; **OPENAI_API_KEY**; **RESEND_API_KEY**; same S3 vars as backend. Do **not** copy CORS_ORIGINS / CORS_ORIGIN_REGEX.
4. Redeploy each service after changing env vars (or use **Manual Deploy**).
