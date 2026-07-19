# How to Run the Tests

## Prerequisites

Ensure your project has the following installed:
```bash
pip install pytest pytest-django django-rest-framework
```

## Test File Placement

Place the test files in your project structure like this:

```
earth-backend/
├── apps/
│   └── submissions/
│       ├── tests/
│       │   ├── __init__.py
│       │   ├── conftest.py          # Shared fixtures
│       │   ├── test_services.py     # Service layer tests
│       │   ├── test_views.py        # API view tests
│       │   └── test_state_machine.py # State machine tests
│       ├── ...
├── tests/
│   └── conftest.py                  # Global fixtures (if any)
├── pytest.ini
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run only submissions app tests
```bash
pytest apps/submissions/tests/
```

### Run a specific test file
```bash
pytest apps/submissions/tests/test_services.py
```

### Run a specific test class
```bash
pytest apps/submissions/tests/test_services.py::TestTransitionItemStatus
```

### Run a specific test method
```bash
pytest apps/submissions/tests/test_services.py::TestTransitionItemStatus::test_pending_to_accepted
```

### Run with verbose output
```bash
pytest -v
```

### Run with coverage
```bash
pytest --cov=apps.submissions --cov-report=html
```

## Test Settings

Create `config/settings/test.py`:

```python
from .base import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Use fast password hashing for tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Disable Celery in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use local media storage for tests
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MEDIA_ROOT = BASE_DIR / "test_media"
```

## What Each Test Covers

### `test_services.py` (15 tests)
- **State transitions**: PENDING→ACCEPTED, PENDING→REJECTED, ACCEPTED→DISPATCHED
- **Invalid transitions**: All illegal jumps return 400 (not 500)
- **Terminal states**: REJECTED and COMPLETED cannot transition further
- **Photo creation**: Single photo, multiple photos, no photos (400), transaction rollback
- **Driver assignment**: Creates assignment + transitions to DISPATCHED, prevents double-assignment

### `test_views.py` (18 tests)
- **ItemUploadView**: Create with photos, without photos (400), multiple photos, auth required, list filtering
- **SubmissionReviewQueueView**: Admin sees only PENDING items, non-admin blocked
- **SubmissionDecisionView**: Accept, reject with reason, reject without reason (400), invalid action (400), state machine enforcement, non-admin blocked, **400 not 500 bug fix**
- **DriverDispatchView**: Dispatch accepted item, cannot dispatch pending (400), cannot double-dispatch (400), missing fields (400), non-admin blocked

### `test_state_machine.py` (13 tests)
- **Parametrized**: All 13 possible transition combinations
- **Unknown status**: Returns False for unrecognized current status

## Key Test Assertions

| What we're testing | How we verify |
|---|---|
| DRF ValidationError returns 400 | `assert response.status_code == 400` on invalid transitions |
| State machine enforced | Admin can only `accept`/`reject`, not set arbitrary status |
| Photos required | `assert "photos" in str(response.data)` |
| Transaction safety | `assert Item.objects.count() == 0` after failed creation |
| Driver assignment | `assert item.dispatch.driver_name == "John Doe"` |
| Terminal states | `pytest.raises(DRFValidationError)` on REJECTED→ACCEPTED |
