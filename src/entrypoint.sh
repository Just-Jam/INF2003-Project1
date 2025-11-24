#!/bin/sh
set -e

echo "Waiting for Postgres to be ready..."

# Retry until Postgres accepts a connection. Requires psycopg2 installed in the image.
until python - <<PY
import os, sys
try:
    import psycopg2
    conn = psycopg2.connect(
        dbname=os.getenv('POSTGRES_DB') or os.getenv('POSTGRES_DB', ''),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('DB_HOST', 'db'),
        port=os.getenv('DB_PORT', '5432'),
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    print("Postgres not ready:", e)
    sys.exit(1)
PY
do
  sleep 1
done

echo "Running migrations"
python manage.py makemigrations
python manage.py makemigrations core
python manage.py migrate

echo "Starting server"
exec python manage.py runserver 0.0.0.0:8000

