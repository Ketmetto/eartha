# Eartha — Production Deployment Guide

Docker Compose stack on a Hostinger VPS. No CI/CD — deploys are manual
(`git pull` + `docker compose up -d --build`).

---

## Required `.env.prod` values

Copy `.env.example` → `.env.prod` on the server (never commit it).

| Variable | Notes |
|---|---|
| `DJANGO_SECRET_KEY` | Fresh value, don't reuse the dev key: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | Must be `False` |
| `ALLOWED_HOSTS` | Real domain(s), e.g. `yourdomain.com,www.yourdomain.com` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Real password, not `change-me`. Only takes effect the first time the Postgres volume initializes — set it correctly before the first `up`, or you'll need `ALTER USER` inside the running container to change it after |
| `POSTGRES_HOST` / `POSTGRES_PORT` | `db` / `5432` (Docker network defaults, already correct) |
| `REDIS_URL` | `redis://redis:6379/0` (already correct) |
| `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_PORT` / `DEFAULT_FROM_EMAIL` | Verification emails, password resets, and points/status notifications silently fail to send without these — prod has no console-log fallback. Uses Brevo: `EMAIL_HOST=smtp-relay.brevo.com`, `EMAIL_PORT=587`, `EMAIL_HOST_USER` is the generated SMTP login Brevo shows you, `EMAIL_HOST_PASSWORD` is the SMTP key from Brevo's SMTP & API settings, `DEFAULT_FROM_EMAIL` must be a verified sender in Brevo |
| `CORS_ALLOWED_ORIGINS` | Real frontend origin(s), comma-separated, no trailing slash |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Needed for Google/Apple login. Minify the service-account JSON to one line: `python -c "import json;print(json.dumps(json.load(open('key.json'))))"` |
| `FIREBASE_API_KEY` / `FIREBASE_AUTH_DOMAIN` / `FIREBASE_PROJECT_ID` / `FIREBASE_APP_ID` | Public client-side Firebase config, from Firebase console → Project Settings |
| `GOOGLE_MAPS_API_KEY` | Optional — blank means pickup-address fields stay plain text inputs. Restrict by HTTP referrer in Google Cloud Console if set |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_STORAGE_BUCKET_NAME` / `AWS_S3_ENDPOINT_URL` | Optional — blank falls back to local disk (fine short-term, but no CDN and files live in the `media_data` volume) |
| `SENTRY_DSN` | Optional — blank means error tracking is a no-op |

Also replace the domain placeholder in two places:
- `nginx/nginx.conf` — `server_name` lines in both the `:80` and `:443` blocks
- `config/settings/prod.py` — `CSRF_TRUSTED_ORIGINS`

---

## One-time server setup (Hostinger VPS)

1. **Point DNS at the server.** Create an `A` record for the domain and
   `www` subdomain pointing at the VPS's public IP. Wait for propagation
   (`dig yourdomain.com` returns the right IP) before continuing —
   Certbot fails otherwise.

2. **Install Docker + Compose:**
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   # log out and back in for the group change to apply
   ```

3. **Open firewall ports 80 and 443:**
   ```bash
   sudo firewall-cmd --permanent --add-port=80/tcp
   sudo firewall-cmd --permanent --add-port=443/tcp
   sudo firewall-cmd --reload
   ```

4. **Clone the repo, create `.env.prod`** with the values above.

5. **Set up swap** (one-time, host-level — see Resource limits below):
   ```bash
   fallocate -l 2G /swapfile
   chmod 600 /swapfile
   mkswap /swapfile
   swapon /swapfile
   echo '/swapfile none swap sw 0 0' >> /etc/fstab
   ```
   Verify with `free -h` — `Swap:` should show 2.0G total.

---

## Resource limits (KVM1, 4 GB RAM total)

`docker-compose.prod.yml` sets explicit `deploy.resources.limits.memory`
per service — without it, an unbounded Postgres or Redis under load can
starve Gunicorn or Celery, and because every service is
`restart: unless-stopped`, an OOM kill shows up as a mystery 502 with no
obvious cause in the logs.

| Service | Limit | Notes |
|---|---|---|
| `web` (Gunicorn, 3 workers) | 1 GB | Watch this first if image uploads grow |
| `celery` | 300 MB | `--concurrency=2` |
| `db` (Postgres) | 512 MB | `shared_buffers=256MB`, `max_connections=50` |
| `redis` | 150 MB | `maxmemory 128mb`, `allkeys-lru` eviction |
| Nginx + certbot + host OS | ~500 MB | not containerized-limited, informal budget |

Total reserved ~2.5 GB, leaving ~1.5 GB headroom. If a service is
consistently near its limit, raise that limit (and drop headroom
elsewhere) or upgrade to KVM2 — don't just remove the limit, since that
turns a visible constraint back into a random OOM kill. The swap step
above is a second line of defense for brief spikes, not a substitute for
right-sizing these limits.

---

## First deploy — bootstrapping the TLS certificate

Certbot can't issue a certificate until Nginx is running on port 80, but
Nginx's HTTPS block won't start without a certificate that doesn't exist
yet.

**Step 1 — comment out the `server { listen 443 ... }` block** in
`nginx/nginx.conf` temporarily, so only the port-80 block exists. Then:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

**Step 2 — request the certificate:**
```bash
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d yourdomain.com -d www.yourdomain.com \
  --email you@youremail.com --agree-tos --no-eff-email
```

**Step 3 — restore the full `nginx.conf`** (443 block back in), then:
```bash
docker compose -f docker-compose.prod.yml restart nginx
```

From here on, the `certbot` service's background loop renews
automatically every 12 hours.

---

## Nginx and redeploys: usually no restart needed

A bare `proxy_pass http://web:8000` would resolve `web`'s address once,
at config load, and cache it — so a redeployed `web` (new internal IP)
would get `502`s until Nginx was restarted. `nginx/nginx.conf` avoids
this by routing through a variable with `resolver 127.0.0.11 valid=10s`
(Docker's embedded DNS), forcing Nginx to re-resolve `web` every 10
seconds instead of once at startup.

If a 502 ever outlives ~30 seconds after a deploy, reload Nginx:
```bash
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

Editing `nginx/nginx.conf` itself (not just redeploying `web`) always
needs that same reload to take effect.

---

## Gotcha: don't delete/recreate the static or media volumes casually

The `static_data` and `media_data` named volumes only get correct
permissions because `Dockerfile` pre-creates those directories with the
right owner *before* the volume is first created and populated. Don't
remove the `RUN mkdir -p /app/staticfiles /app/media` line thinking it's
redundant — without it, fresh volumes get created as `root`-owned and
the non-root `app` user gets `PermissionError: [Errno 13]` writing
static files or uploads.

---

## Normal deploy from then on

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

No Nginx restart needed. Migrations and `collectstatic` run
automatically via the entrypoint script before Gunicorn starts.

---

## Backups

A volume is not a backup. `~/backup.sh` on the VPS runs nightly via cron
(`0 3 * * * /home/akrm/backup.sh >> /home/akrm/backups/backup.log 2>&1`)
and does all of this:

1. `pg_dump`s the database, gzips it to `~/backups/eartha-<date>.sql.gz`.
2. Tars the `media_data` volume (item photos, benefit logos, Site Content
   images) to `~/backups/eartha-media-<date>.tar.gz` — via
   `docker compose run --entrypoint tar ... web`, which reuses the `web`
   service's own `/app/media` mount instead of hardcoding the
   compose-prefixed volume name (e.g. `eartha_media_data`).
3. Pushes both files to a Backblaze B2 bucket (`s3://eartha`, S3-compatible
   endpoint, `aws` CLI with a `backblaze` named profile) — real offsite
   storage, not just another copy on the same disk.
4. Deletes local copies older than 7 days (`find ... -mtime +7 -delete`).
   The B2 copies aren't rotated by this script — set a lifecycle rule on
   the bucket if you want them to expire too.

To verify it's actually working (not just installed):
```bash
cat ~/backups/backup.log
aws s3 ls s3://eartha/ --endpoint-url https://s3.eu-central-003.backblazeb2.com --profile backblaze
```
Both DB and media files should show up dated today after a run.

Docker won't delete a volume still referenced by a container under a
*different* compose project name — check `docker volume ls` for orphaned
volumes before assuming data from an old `docker volume rm` is gone.

---

## Post-deploy checklist

- [ ] `https://yourdomain.com` loads with a valid padlock, no mixed content
- [ ] `http://yourdomain.com` redirects to `https://`
- [ ] Static files (CSS/JS/admin styling) load correctly — if unstyled,
      check the static volume permissions gotcha above
- [ ] Uploaded images (e.g. benefit logos) load correctly from `/media/`
- [ ] Django admin login works without a CSRF error (confirms
      `CSRF_TRUSTED_ORIGINS` matches the real domain)
- [ ] `DEBUG=False` confirmed (a broken URL shows a plain error page, not
      a stack trace)
- [ ] Celery worker logs show it connected to Redis and Postgres
- [ ] Google/Apple login works (confirms `FIREBASE_SERVICE_ACCOUNT_JSON`
      parsed — check `web`/`celery` logs for an Admin SDK init error
      otherwise)
- [ ] Swap is active: `free -h` shows `Swap: 2.0G` total
- [ ] After first real traffic, `docker stats` for a few minutes and
      confirm no service is pinned at its memory limit
- [ ] Cron backup job runs successfully once, and both the `.sql.gz` and
      `eartha-media-*.tar.gz` show up locally and in the B2 bucket
