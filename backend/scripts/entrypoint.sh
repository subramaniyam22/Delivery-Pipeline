#!/bin/sh
# Backend entrypoint: run migrations then start the app.
# Used by Docker and Render for parity.

set -e

# Run migrations if alembic is present (required so DB has all columns, e.g. job_runs.correlation_id)
if [ -f /app/alembic.ini ] && command -v alembic >/dev/null 2>&1; then
  echo "Running database migrations..."
  if ! alembic upgrade head; then
    echo "Migrations failed. Fix the database and restart." >&2
    exit 1
  fi
  echo "Migrations complete."
fi

# Start the app (default: uvicorn; override with CMD or docker command)
exec "$@"
