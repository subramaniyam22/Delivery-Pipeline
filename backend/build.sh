#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed admin user if needed
python scripts/seed_admin.py || true
