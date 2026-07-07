#!/bin/sh
# entrypoint.sh — Run Alembic migrations then start Uvicorn
# This file is copied to /entrypoint.sh in the Docker container.
set -e

echo "=== Argus Gateway Starting ==="
echo ">>> Working directory: $(pwd)"

echo ">>> Running database migrations..."
# alembic.ini is copied into the /app directory (from gateway/),
# and script_location in the container-local alembic.ini is "migrations/"
alembic upgrade head
echo ">>> Migrations complete."

echo ">>> Starting Uvicorn server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
