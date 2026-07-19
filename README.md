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

```bash
pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

## To create a superuser
```bash

docker compose exec web python manage.py createsuperuser
```

## Open decision

Points-per-condition criteria currently ships as a static table
(`apps/points/rules.py`). If a configurable rules engine is needed
instead, that's the only file that changes.

## Structure

- `config/` — settings, root URLs, Celery/WSGI/ASGI entrypoints
- `apps/users` — auth, profile, RBAC
- `apps/submissions` — upload flow, admin review, driver dispatch
- `apps/points` — ledger, benefits, redemption
- `apps/engagement` — contact form, partner inquiries, public stats
- `base/` — shared base model, permissions, pagination, storage
- `notifications/` — Celery tasks + provider adapters, used by every app
