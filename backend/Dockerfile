FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    curl \
    nodejs \
    npm \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Lighthouse and Playwright browsers to a fixed path (so runtime finds them when HOME=/opt/render on Render)
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.cache/ms-playwright
ENV PATH="/usr/local/bin:$PATH"
RUN npm install -g lighthouse \
    && mkdir -p /app/.cache/ms-playwright \
    && python -m playwright install --with-deps chromium

# Copy application code
COPY . .

# Ensure entrypoint has LF line endings (avoids "no such file or directory" when shebang has CRLF)
RUN sed -i 's/\r$//' /app/scripts/entrypoint.sh 2>/dev/null || true
# Create upload directory and make entrypoint executable
RUN mkdir -p /uploads && chmod +x /app/scripts/entrypoint.sh

# Expose port
EXPOSE 8000

# Use shell form so $PORT from Render (or default 8000) is applied at runtime
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind "0.0.0.0:${PORT:-8000}" --timeout 60 --keep-alive 5
