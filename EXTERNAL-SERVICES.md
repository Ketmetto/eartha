# External Services

Every third-party service this app depends on — what it's for, where its
config lives, where to get/rotate credentials, and current status. For the
actual `.env.prod` key names and required/optional status, see
`DEPLOYMENT-KEYS-AND-ISSUES.md`; this doc is the "what is this and why do
we have it" companion to that checklist.

---

## Firebase (Google sign-in)

**What**: Social login. `firebase-auth-compat.js` (loaded from Google's CDN
in `login.html`, not the `firebase` npm package in `package.json` — that
dependency is unused dead weight, nothing in `apps/` imports it) handles
the client-side popup flow; the backend verifies tokens via the Firebase
Admin SDK. Apple sign-in was removed (`945b027`, "was broken and
misleading") — Google is the only working social login path.

**Config**: `FIREBASE_SERVICE_ACCOUNT_JSON` (server-side, from a service
account key — minify to one line before putting in `.env.prod`),
`FIREBASE_API_KEY` / `FIREBASE_AUTH_DOMAIN` / `FIREBASE_PROJECT_ID` /
`FIREBASE_APP_ID` (public client-side values).

**Console**: Firebase console → Project Settings, for both the service
account key and the client config values.

**Status**: Configured and working.

---

## Brevo (transactional email)

**What**: Registration verification, password reset, points/status
notification emails. `django.core.mail.backends.smtp.EmailBackend` talks
to it over SMTP — there's no Brevo-specific SDK/library involved, it's
generic SMTP config.

**Config**: `EMAIL_HOST=smtp-relay.brevo.com`, `EMAIL_PORT=587`,
`EMAIL_HOST_USER` (a generated login Brevo shows you, looks like
`xxxxxx001@smtp-brevo.com` — not your account email), `EMAIL_HOST_PASSWORD`
(an SMTP key, not your account password), `DEFAULT_FROM_EMAIL` (must be a
sender verified in Brevo).

**Console**: Brevo dashboard → SMTP & API settings, for the login/key pair
and sender verification.

**Status**: Configured and working. (Both `DEPLOYMENT.md` and
`DEPLOYMENT-KEYS-AND-ISSUES.md` previously documented SendGrid instead —
fixed; the actual provider has been Brevo since `d4bf173`.)

---

## Google Maps Platform

**What**: Address autocomplete, geocoding, and the pin-drop map on the
upload/profile pages (`apps/web/static/web/js/address-autocomplete.js`).
Loaded dynamically client-side, not server-side.

**Config**: `GOOGLE_MAPS_API_KEY` — client-side, restrict by HTTP referrer
in Google Cloud Console once set.

**Console**: Google Cloud Console → APIs & Services → Credentials.

**Status**: Configured and working. Optional — blank just means pickup
address fields stay plain text inputs instead of autocomplete.

---

## Backblaze B2 (offsite backups)

**What**: Nightly destination for the Postgres dump + media tarball —
see `DEPLOYMENT.md`'s "Backups" section for what `~/backup.sh` actually
does. Uses the `aws` CLI pointed at B2's S3-compatible endpoint, not the
`b2` CLI or `rclone`.

**Config**: Lives entirely on the VPS, outside `.env.prod` — an
`~/.aws/config`/`~/.aws/credentials` profile named `backblaze`, referenced
via `--profile backblaze --endpoint-url https://s3.eu-central-003.backblazeb2.com`
in `backup.sh`. Bucket: `eartha`.

**Console**: Backblaze B2 dashboard → Application Keys, for
rotating/creating the key pair behind the `backblaze` AWS profile.

**Status**: Configured and working, confirmed via a real manual run
(2026-08-17) — both the DB dump and a 42MB media tarball landed in the
bucket.

---

## AWS S3 (optional media storage — currently unused)

**What**: Not the same thing as the Backblaze setup above, despite both
being S3-compatible — this is `django-storages`' wiring for serving
*live* media (item photos, benefit logos, Site Content images) from a
CDN-backed bucket instead of local disk. Backblaze is a backup
destination; this would be where the actual files live day-to-day.

**Config**: `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` /
`AWS_STORAGE_BUCKET_NAME` / `AWS_S3_ENDPOINT_URL`.

**Status**: Not configured — all blank. Media falls back to local disk in
the `media_data` Docker volume (`config/settings/prod.py`'s
`FileSystemStorage` fallback). This is covered by the nightly Backblaze
media backup either way, so it's a "nice to have a CDN" gap, not a data-
loss risk.

---

## Sentry (optional error tracking)

**What**: Exception tracking for `web`/`celery`, via `sentry-sdk`
(`config/settings/prod.py` and `staging.py`).

**Config**: `SENTRY_DSN`.

**Console**: Sentry → Project Settings → Client Keys (DSN), for creating
or rotating the DSN.

**Status**: Confirmed blank on the real VPS (2026-08-17) — error tracking
is currently a silent no-op in production. Not broken, just off: an
unhandled 500 shows the user a plain error page and nobody gets notified,
since there's nowhere for it to report to.

---

## Hostinger (VPS host)

**What**: The `eartha.me` VPS itself (Docker Compose stack — see
`DEPLOYMENT.md`). Also provides its own weekly panel-level VPS snapshots,
separate from and in addition to the Backblaze backups above — configured
in Hostinger's hPanel, not in this repo or any script.

**Console**: hPanel, for snapshot schedule/retention and VPS management.

**Status**: Live.

---

## WhatsApp (wa.me links)

**What**: Not an API integration — just plain `https://wa.me/<number>`
deep links, no account or credentials involved. Used three ways: the
contact page's "WhatsApp Us" link (a fixed business number in
`contact.html`), a phone-verification nudge on upload/profile
(`Eartha.whatsappVerifyUrl` in `store.js` — "not real SMS verification,
just a free nudge"), and driver dispatch (`queue.js` builds a pickup-
details message link for whichever driver a submission is assigned to).

**Status**: Working, nothing to configure or rotate.

---

## Dead config — not actually wired up

`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `APPLE_CLIENT_ID` /
`APPLE_CLIENT_SECRET` / `APPLE_KEY_ID` are read into `django-allauth`
settings (`config/settings/base.py`) but allauth's URLs are never
registered in `config/urls.py` — this is leftover from before Firebase
became the social-login path. Safe to ignore; not needed for anything
currently working.
