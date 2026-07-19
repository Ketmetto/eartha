#!/bin/sh
set -e

# Wait for Postgres to actually accept connections — depends_on only
# waits for the container to start, not for the DB to be ready.
python - <<'PY'
import os
import socket
import sys
import time

host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))

for attempt in range(1, 31):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("[entrypoint] PostgreSQL is accepting connections.")
            break
    except OSError as exc:
        print(f"[entrypoint] waiting for PostgreSQL at {host}:{port} ({attempt}/30): {exc}")
        time.sleep(2)
else:
    sys.exit(f"[entrypoint] ERROR: PostgreSQL at {host}:{port} never became ready.")
PY

# Both web and celery share this entrypoint, but only one process should
# ever run migrations — otherwise they race on creating django_migrations
# and one crashes with a duplicate-key error. web owns schema setup;
# celery just waits for Postgres/Redis and starts straight into its CMD.
case "$1" in
    celery)
        echo "[entrypoint] celery worker — skipping migrate/collectstatic"
        ;;
    *)
        python manage.py migrate --noinput
        python manage.py collectstatic --noinput
        ;;
esac

exec "$@"
