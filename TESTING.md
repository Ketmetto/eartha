# Testing

How to run the test suite, how it's organized, and the conventions every
test file follows. This covers every app: `users`, `submissions`,
`points`, `engagement`. (`web` is templates + static JS with no Python
views of its own — nothing to unit test there yet.)

## Running tests

Inside the dev container (or any environment with the `dev` extra
installed):

```bash
# everything
pytest

# one app
pytest apps/points/

# one file
pytest apps/points/tests/test_services.py

# one class
pytest apps/points/tests/test_services.py::TestRedeemBenefit

# one test
pytest apps/points/tests/test_services.py::TestRedeemBenefit::test_raises_when_balance_is_insufficient

# see print()/logging output
pytest -s
```

Via Docker Compose, from the host:

```bash
docker compose exec web pytest
```

### Why `pytest` alone is safe to run in the dev container

The dev container sets `DJANGO_SETTINGS_MODULE=config.settings.dev` so
`manage.py runserver` talks to the real Postgres/Redis services. Tests
must **not** use that — they need `config.settings.test` (in-memory
SQLite, in-process cache, eager Celery, in-memory file storage), or
they'd hit real infra and leak state between runs.

`pyproject.toml`'s `[tool.pytest.ini_options]` forces this with
`--ds=config.settings.test` in `addopts`. That's a `--ds` flag, not just
the `DJANGO_SETTINGS_MODULE` ini key, because pytest-django prioritizes
the environment variable over the ini file — without `--ds`, the
env var would win and tests would silently run against dev's real
services. Don't remove that flag, and don't set `DJANGO_SETTINGS_MODULE`
yourself before running `pytest`.

## What's covered, per app

| App | Files | Covers |
|---|---|---|
| `users` | `test_auth.py`, `test_profile.py`, `test_firebase_login.py`, `test_email_change.py` | register, email-verified login/refresh, `/me/`, RBAC on a protected endpoint, address/notification-prefs CRUD, change password, Firebase social login, email-verified-flag survives profile edits, phone/email normalization + uniqueness, pending email change confirm flow |
| `submissions` | `test_state_machine.py`, `test_services.py`, `test_views.py` | every status transition (parametrized), photo-validated item creation (including SVG/spoofed-content-type rejection and HEIC acceptance), driver dispatch, the review/decision/dispatch admin endpoints |
| `points` | `test_rules.py`, `test_services.py`, `test_views.py` | ledger balance math, admin-configurable category/condition award rules, redemption (success/insufficient-balance/unique codes), benefit list + category filter, admin benefit CRUD/reorder |
| `engagement` | `test_views.py` | public contact form + partner-inquiry flag, public impact stats, admin inbox + resolve, admin dashboard aggregate stats |

## Shared fixtures

Defined once in the root `conftest.py`, available to every app's tests
without importing anything:

| Fixture | What it gives you |
|---|---|
| `api_client` | Plain unauthenticated `rest_framework.test.APIClient` |
| `user` | A regular, **email-verified** user (`verified=True`) — verified so login-flow tests don't also have to think about email verification just to authenticate |
| `admin_user` | Same, plus `is_staff=True` — for `IsAdmin`-gated endpoints |
| `auth_client` | `api_client` pre-authenticated as `user` |
| `admin_client` | `api_client` pre-authenticated as `admin_user` |

App-specific fixtures (domain objects like `pending_item`, `benefit`)
live in that app's own `tests/conftest.py`. **Rule of thumb:** if a
fixture is generic enough that a second app would want the same thing,
it belongs in the root `conftest.py`, not duplicated locally — don't
redefine `user`/`api_client`/etc. in an app's local conftest.

## Conventions

- One test class per view or service function, named `Test<Thing>`.
- Class body starts with the endpoint's `url` where it's a static path;
  reverse() it inline (or as a method) when it needs a kwarg like a pk.
- Every endpoint test includes an auth/permission case first
  (`test_requires_authentication` / `test_non_admin_cannot_access`),
  then the behavior cases.
- Mock at the point of use, not the point of definition. Notification
  tasks are imported *inside* the calling function (so the import binds
  fresh each call) — patch the task's home module
  (`notifications.tasks.notify_points_awarded`), not the caller's module
  path (`apps.points.services.notify_points_awarded`), or the mock silently
  won't apply and a real Celery task will queue.
- Use `pytest.raises(...)` for service-layer errors, HTTP status
  assertions for view-layer errors — don't re-test the same failure at
  both layers.
- `@pytest.mark.django_db` on every class that touches the ORM (or use a
  fixture that depends on `db`, which most already do transitively).

## Adding tests for a new module

1. `mkdir apps/<app>/tests && touch apps/<app>/tests/__init__.py` if it
   doesn't exist yet.
2. Add a `conftest.py` there only for fixtures unique to that app's
   domain objects.
3. Mirror the existing split: `test_services.py` for business logic
   (no HTTP involved), `test_views.py` for the API surface.
4. Reuse `user` / `admin_user` / `auth_client` / `admin_client` from the
   root conftest rather than rebuilding them.
