# Eartha backend

Django 5 + DRF backend for Eartha — auth, submissions, points/rewards, admin
review & dispatch, benefits, contact/inquiries, public impact stats.

## Local dev

```bash
cp .env.example .env        # fill in DJANGO_SECRET_KEY at minimum
docker compose up
docker compose exec web python manage.py migrate
docker compose exec web python manage.py shell < scripts/seed_data.py
```

API is served at `http://localhost:8000/api/v1/`.
Demo accounts (after seeding): `demo@eartha.co` / `demo1234`, `admin@eartha.co` / `admin123`.

## Without Docker

`.env.example`'s `POSTGRES_HOST=db` and `REDIS_URL=redis://redis:6379/0`
are Docker Compose service names — they don't resolve outside the
Compose network. Running natively, point both at wherever your own
Postgres/Redis actually listen (typically `localhost`):

```bash
cp .env.example .env
# then edit .env: POSTGRES_HOST=localhost, REDIS_URL=redis://localhost:6379/0
pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

You'll need Postgres and Redis running locally yourself (e.g. via your
OS package manager or `docker compose up db redis` if you want to keep
using Docker for just the data stores).

## To create a superuser
```bash

docker compose exec web python manage.py createsuperuser
```

## Deploying

See `DEPLOYMENT.md` for the Hostinger VPS / Docker Compose production
setup, and `DEPLOYMENT-KEYS-AND-ISSUES.md` for the required `.env.prod`
values plus known issues/open items.

## Structure

- `config/` — settings, root URLs, Celery/WSGI/ASGI entrypoints
- `apps/users` — auth, profile, RBAC
- `apps/submissions` — upload flow, admin review, driver dispatch
- `apps/points` — ledger, benefits, redemption
- `apps/engagement` — contact form, partner inquiries, public stats
- `base/` — shared base model, permissions, pagination, storage
- `notifications/` — Celery tasks + provider adapters, used by every app
