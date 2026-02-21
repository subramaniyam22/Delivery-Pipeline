# Worker image: Python + Node 20 + Lighthouse + Chromium + Playwright
# Build context: repo root. Copy backend app and install all job-runner deps.
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# System deps: curl, ca-certificates, gnupg (for Node), postgresql-client (optional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    postgresql-client \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Node 20 (NodeSource)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Lighthouse (global, pinned for predictable runs)
RUN npm install -g lighthouse@11
RUN lighthouse --version

# Fonts (improves Lighthouse screenshots/layout accuracy)
RUN apt-get update && apt-get install -y fonts-liberation fonts-noto-color-emoji && rm -rf /var/lib/apt/lists/*

# Chromium (Debian package) for Lighthouse
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Python deps from backend
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Playwright + Chromium browser
RUN pip install playwright \
    && playwright install --with-deps chromium

# Backend application code (worker runs as python -m app.jobs.worker)
COPY backend/app /app/app

# Create upload directory
RUN mkdir -p /uploads

# No exposed port (worker is a consumer)
CMD ["python", "-m", "app.jobs.worker"]
