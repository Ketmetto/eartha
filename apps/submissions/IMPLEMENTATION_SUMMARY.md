# Submissions Module — Implementation Summary

## Files Modified/Created

### 1. `apps/submissions/services.py` (Rewritten)
- **Bug Fix**: Changed `from django.base.exceptions import ValidationError` → `from rest_framework.exceptions import ValidationError`
  - DRF's `ValidationError` is caught by DRF's exception handler and returns a proper 400 response.
  - Django's `ValidationError` would surface as an unhandled 500.
- **New function**: `create_item_with_photos()` — creates an Item only if at least one valid photo is provided. All photos saved inside a single transaction.
- **New function**: `assign_driver()` — creates a `DriverAssignment` for an ACCEPTED item, transitions it to DISPATCHED via the state machine, and updates the assignment status.

### 2. `apps/submissions/serializers.py` (Extended)
- **New**: `ItemCreateWithPhotosSerializer` — validates item creation input including photo list (min 1, max 10).
- **New**: `SubmissionDecisionSerializer` — validates admin decision (`accept`/`reject`). Enforces rejection_reason when rejecting.
- **New**: `DriverDispatchSerializer` — validates driver assignment input (driver_name, pickup_address_snapshot).

### 3. `apps/submissions/admin_views.py` (Rewritten)
- **Rewritten**: `SubmissionDecisionView` — no longer a raw `UpdateAPIView`. Now a `GenericAPIView` that:
  - Accepts POST with `{"action": "accept"}` or `{"action": "reject", "rejection_reason": "..."}`
  - Drives the state machine via `transition_item_status()` — admins cannot bypass the state machine.
  - Returns the updated item via `ItemAdminSerializer`.
- **New**: `DriverDispatchView` — admin endpoint to assign a driver to an accepted item:
  - POST `{"driver_name": "...", "pickup_address_snapshot": "..."}`
  - Calls `assign_driver()` service which creates the assignment and transitions the item.

### 4. `apps/submissions/views.py` (Rewritten)
- **Rewritten**: `ItemUploadView.create()` — overrides default create to use `create_item_with_photos()` service.
  - Validates input via `ItemCreateWithPhotosSerializer`.
  - Extracts photos from `request.FILES.getlist("photos")`.
  - Returns 400 if no photos provided.
  - Creates item + photos in a single transaction.

### 5. `apps/submissions/urls.py` (Extended)
- Added new route: `admin/<uuid:pk>/dispatch/` → `DriverDispatchView`

## State Machine Enforcement

The state machine in `state_machine.py` remains unchanged:

```
PENDING → {ACCEPTED, REJECTED}
ACCEPTED → {DISPATCHED}
DISPATCHED → {COLLECTED}
COLLECTED → {COMPLETED}
REJECTED → {}
COMPLETED → {}
```

All status transitions now go through `transition_item_status()` which calls `can_transition()`.

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET/POST | `/submissions/` | User | List own submissions / Create with photos |
| GET | `/submissions/admin/queue/` | Admin | Pending submissions queue |
| POST | `/submissions/admin/<uuid:pk>/decision/` | Admin | Accept or reject (drives state machine) |
| POST | `/submissions/admin/<uuid:pk>/dispatch/` | Admin | Assign driver & dispatch item |

## Key Design Decisions

1. **DRF ValidationError**: Ensures all validation errors return 400, not 500.
2. **Service Layer**: Business logic lives in `services.py`, not views/serializers — testable and reusable.
3. **Transactions**: Item creation and driver assignment are wrapped in `transaction.atomic()`.
4. **State Machine**: Admin cannot bypass — `SubmissionDecisionView` only accepts `accept`/`reject` actions, not raw status values.
5. **Circular Import Avoidance**: Points award and notifications are imported lazily inside functions.
