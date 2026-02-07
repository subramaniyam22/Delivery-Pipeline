#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

# Run database migrations
alembic upgrade heads

# Create Notifications Table (if missing)
python create_notifications_table.py || true

# Seed admin user if needed
python scripts/seed_admin.py || true
