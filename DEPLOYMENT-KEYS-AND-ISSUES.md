# Deployment Keys & Pre-Launch Issues

Current as of the `eartha.me` VPS deploy. Re-verified against the actual
`config(...)` calls in `config/settings/*.py`, not just the previous pass's
notes — some of what follows supersedes earlier versions of this file.

---

## 1. Email — the "read the verification link from the terminal" workflow does not exist in prod

All of this session's local testing used `EMAIL_BACKEND=console`
(`config/settings/dev.py` — falls back to console automatically whenever
`EMAIL_HOST` is unset), which prints emails to `docker logs` instead of
sending them. That's how registration/password-reset links got read out of
the container logs during testing.

`config/settings/prod.py` has **no such fallback** —
`EMAIL_BACKEND` defaults to real SMTP
(`django.core.mail.backends.smtp.EmailBackend`), and `EMAIL_HOST` /
`EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `DEFAULT_FROM_EMAIL` all default
to blank. If those are blank on the VPS, every email-triggering action —
registration verification, password reset, points/status notifications —
will fail outright (SMTP connection error to an empty host) the moment a
real user hits it.

**Two things to check on the VPS right now** (check key *names* only, per
this session's rule of never printing real secret values):

```bash
grep -c "^EMAIL_HOST=$\|^EMAIL_HOST_PASSWORD=$\|^DEFAULT_FROM_EMAIL=$" .env.prod
```
A non-zero count means at least one required email field is still blank.

```bash
grep "^EMAIL_BACKEND=" .env.prod
```
If this line exists at all and says `console` (or anything other than the
real SMTP backend), **prod will silently "succeed" at sending emails that
never actually leave the server** — no error, just a link nobody receives.
This is an easy thing to accidentally carry over if `.env.prod` was ever
bootstrapped by copying values from a local testing file. If present,
delete the line entirely (let it fall back to the real SMTP default) or
set it explicitly to `django.core.mail.backends.smtp.EmailBackend`.

No code changes are needed for this — it's purely a `.env.prod` fill-in +
verification step. For SendGrid specifically: `EMAIL_HOST=smtp.sendgrid.net`,
`EMAIL_HOST_USER=apikey` (that literal string, not your account name),
`EMAIL_HOST_PASSWORD=` your SendGrid API key, `DEFAULT_FROM_EMAIL=` a
sender verified in SendGrid's Sender Authentication settings.

**Test it for real once filled in** — register a throwaway account against
the live site and confirm the verification email actually arrives, rather
than trusting the config alone.

---

## 2. Keys and values checklist for `.env.prod`

| Variable | Required? | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | **Yes** | Fresh, not the dev key |
| `DEBUG` | **Yes** | Must be `False` |
| `ALLOWED_HOSTS` | **Yes** | `eartha.me,www.eartha.me` |
| `DJANGO_SETTINGS_MODULE` | **Yes** | `config.settings.prod` |
| `POSTGRES_DB` / `POSTGRES_USER` | **Yes** | Any real values, consistent with what Postgres was initialized with |
| `POSTGRES_PASSWORD` | **Yes** | A real password — only takes effect on Postgres's first-ever startup on a fresh volume; changing it later needs `ALTER USER` inside the running container too |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Yes (defaults ok) | `db` / `5432` |
| `REDIS_URL` | Yes (default ok) | `redis://redis:6379/0` |
| `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_PORT` / `DEFAULT_FROM_EMAIL` | **Yes** | See section 1 above |
| `EMAIL_BACKEND` | **Should be absent** | See section 1 — only set this if you deliberately want to override the real-SMTP default |
| `CORS_ALLOWED_ORIGINS` | **Yes** | Real origin(s), no trailing slash |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Required for Google/Apple login | Minified to one line. Blank → `apps/users/apps.py`'s `AppConfig.ready()` just skips Firebase init entirely (confirmed graceful no-op) — social login returns a clean "not configured" error instead of crashing, but won't work |
| `FIREBASE_API_KEY` / `FIREBASE_AUTH_DOMAIN` / `FIREBASE_PROJECT_ID` / `FIREBASE_APP_ID` | Required for Google/Apple login | Public client-side values, safe to expose. From Firebase console → Project Settings |
| `GOOGLE_MAPS_API_KEY` | Optional | Client-side, restrict by HTTP referrer in Google Cloud Console. Blank → address fields stay plain text inputs |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_STORAGE_BUCKET_NAME` / `AWS_S3_ENDPOINT_URL` | Optional | Blank → media (item photos, benefit logos, Site Content images) falls back to local disk in the `media_data` volume — no CDN, and it's one more thing that needs backing up (see section 4) |
| `SENTRY_DSN` | Optional | Blank → error tracking is a no-op |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `APPLE_CLIENT_ID` / `APPLE_CLIENT_SECRET` / `APPLE_KEY_ID` | **Not needed** | Wired into `django-allauth` settings but allauth's URLs are never registered in `config/urls.py` (`grep -rn allauth config/urls.py apps/*/urls.py` returns nothing) — dead config. The only working social login path is Firebase. |

### Non-`.env` config — already done
- `nginx/nginx.conf` and `config/settings/prod.py`'s `CSRF_TRUSTED_ORIGINS` — both already point at `eartha.me`/`www.eartha.me`.
- TLS — real Certbot cert issued and swapped in on the VPS (self-signed lines commented out, `/etc/letsencrypt/live/eartha.me/...` active). Remember: that swap lives only on the VPS's local checkout, never committed back to git.

---

## 3. Missing / dead links and stub features

Found by grepping every template for `href="#"` and stub click handlers —
worth a pass before pointing real users at the site:

- **`contact.html`** — Instagram and LinkedIn links are `href="#"`.
- **`login.html` — "Forgot password?"** — `href="#"`, and its click
  handler (`login.js`) just shows a toast: *"PASSWORD RESET COMING
  SOON — CONTACT US MEANWHILE."* This is the most worth fixing of the
  four: the backend (`PasswordResetRequestView` /
  `PasswordResetConfirmView`) is fully implemented and already has test
  coverage — it's just never wired to the login page's UI. A real user
  who forgets their password today has no self-serve way to recover the
  account.
- **`login.html` — "Terms & Privacy Policy"** — `href="#"`, and there's no
  terms/privacy page anywhere in the app (`find . -iname "*terms*" -o
  -iname "*privacy*"` returns nothing). Worth flagging since registration
  requires checking this box (`agree_to_terms`) — right now it links to
  content that doesn't exist.
- **`index.html` newsletter signup** — client-side only. It validates the
  email format and shows *"SIGNED UP — WATCH YOUR INBOX"*, but never
  sends the address anywhere — no backend call at all
  (`apps/web/static/web/js/main.js`, marked `// Hook this up to your
  backend / mail provider later`). Currently misleading: a visitor who
  signs up believes it worked and nothing happens.

---

## 4. Off-Hostinger (offsite) daily backups

`DEPLOYMENT.md` already has the on-server nightly `pg_dump` cron job. That
protects against data loss from app-level mistakes (bad migration, bad
`DELETE`), but not from losing the VPS itself — the dumps live on the same
disk as everything else. Two things worth backing up offsite: the Postgres
dump, and the `media_data` volume if `AWS_STORAGE_BUCKET_NAME` stays blank
(item photos, benefit logos, Site Content images all live there on local
disk).

**Recommended: pull-based, from your own machine** — no new credentials
needed on the VPS at all, since it reuses the SSH access you already have.
Add this as a cron job on your **laptop/local machine**, not the VPS:

```bash
# crontab -e, on your local machine
30 3 * * * rsync -az akrm@191.215.36.244:~/backups/ ~/eartha-backups/ 2>> ~/eartha-backups/rsync.log
```

(Timed 30 minutes after the VPS's own `pg_dump` cron, so the night's dump
file already exists when this runs.) This keeps a rolling local copy
independent of Hostinger entirely — if the VPS is lost, destroyed, or
compromised, the backups aren't lost with it.

**Alternative: push to S3-compatible storage** from the VPS itself, if you'd
rather not depend on your laptop being on/reachable. Since the app already
has S3 wiring (`AWS_ACCESS_KEY_ID` etc.), the same bucket (or a separate
one) can receive backups via a cron job on the VPS using the `aws` CLI or
`s3cmd`. This needs those AWS credentials present on the VPS specifically
for backup purposes — slightly more moving parts than the rsync approach,
but doesn't depend on any single machine being online.

Either way: **for media**, if staying on local-disk storage, back up the
`media_data` volume's contents too, not just the Postgres dump —
`docker run --rm -v eartha_media_data:/data -v ~/backups:/backup alpine tar czf /backup/media-$(date +%F).tar.gz -C /data .`
follows the same pattern as the `pg_dump` cron.

---

## 5. Other open items

Three product decisions are tracked separately in `REMINDERS.txt` (not
duplicated here since that file is the current source of truth for them):
public impact-stats CO2 calculation method, SMS notifications (no provider
configured yet), and the CSP header (needs a dependency decision).

Everything else from earlier passes of this file (redundant deployment
docs, double-wired Firebase credentials, a stale `docker-compose.prod-old.
yml`, missing `ALLOWED_HOSTS` in `.env.example`, staging cookie security,
uninitialized Sentry) has been resolved and folded into the current
`DEPLOYMENT.md`/settings files directly — no longer tracked here to avoid
this file accumulating permanent resolved-history clutter.

---

## 6. Nothing wrong found in

- `Dockerfile` — non-root user, static/media dir pre-creation, entrypoint chaining.
- `scripts/entrypoint.sh` — Postgres wait-loop, and only `web` (not `celery`) runs migrations.
- `docker-compose.prod.yml` — memory limits, healthchecks, volume wiring.
- No secrets tracked in git — `.env`, `.env.prod`, `selfsigned.{crt,key}`, `nginx/nginx.conf.orig` (VPS-only, created during the Certbot bootstrap) are all gitignored or simply never committed.
- No hardcoded credentials, leftover debug `print()`s, or TODO/FIXME markers in application code.
- `EMAIL_BACKEND`/console references — confirmed zero application-code references (`grep -rn "console\|EMAIL_BACKEND" apps/ notifications/`) — it's purely a settings-file concern, not something baked into app logic.
