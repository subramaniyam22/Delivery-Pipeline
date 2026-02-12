#!/usr/bin/env bash
# Run Alembic migrations (ensure PostgreSQL is running and .env DATABASE_URL is set)
set -e
cd "$(dirname "$0")"
python -m alembic upgrade head
echo "Migration completed successfully."
