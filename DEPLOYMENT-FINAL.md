# Eartha — Production Deployment Guide (Final)

This is the single source of truth for deploying to the Hostinger KVM1 VPS.
It merges `DEPLOYMENT.md` and `DEPLOYMENT-kvm1-addendum.md` into one document
— those two files are kept around for history but this is the one to follow.
(`hostinger-kvm1-deployment-plan.md` describes an earlier, different
approach — host-level Nginx instead of containerized — and does not match
the actual `docker-compose.prod.yml`/`nginx/nginx.conf` in this repo; ignore
it.)

No CI/CD is set up yet — deploys are manual (`git pull` +
`docker compose up -d --build`). That's fine for launch; revisit CI/CD later
if deploys become frequent enough to be error-prone.

This guide assumes whoever is deploying is **not** the original developer —
every step below has been tested end-to-end and the gotchas section exists
because we hit each of these for real.

---

## What was missing before, and what changed

| Gap | Fix |
|---|---|
| No TLS / HTTPS | Added `nginx` + `certbot` services |
| Gunicorn exposed directly on `:8000` | Changed `ports` → `expose`; only Nginx is reachable from the internet now |
| No persistent media storage | Added `media_data` volume, mounted into `web` and `celery` |
| No persistent static file serving | Added `static_data` volume, `collectstatic` writes here, Nginx serves it directly |
| Named volumes defaulted to root ownership | `Dockerfile` now pre-creates `/app/staticfiles` and `/app/media` before `chown`, so fresh volumes inherit correct permissions |
| No backup plan for Postgres | Documented below (cron + `pg_dump`) |
| CSRF blocked HTTPS admin logins | Added `CSRF_TRUSTED_ORIGINS` and `SECURE_PROXY_SSL_HEADER` in prod settings |
| Unbounded per-service memory on a 4 GB box | Added `deploy.resources.limits.memory` per service (KVM1-sized, see below) |
| No swap, so a brief memory spike could OOM-kill a container | Documented a one-time swapfile setup below |

The app code and entrypoint script were already solid — migrations,
`collectstatic`, the non-root user, and the Postgres-readiness wait loop all
needed no changes.

---

## Files in this bundle

- `docker-compose.prod.yml` — the production compose file
- `nginx/nginx.conf` — reverse proxy + TLS termination + static/media serving

Edit `nginx/nginx.conf` and replace every `YOURDOMAIN.com` with the real
domain.

Also confirm `config/settings/prod.py` has these two blocks (they should
already be committed, but verify before first deploy):

```python
CSRF_TRUSTED_ORIGINS = [
    "https://YOURDOMAIN.com",
    "https://www.YOURDOMAIN.com",
]

# Nginx terminates TLS and proxies to Gunicorn over plain HTTP internally —
# this tells Django to trust Nginx's X-Forwarded-Proto header instead of
# treating every request as insecure.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

Replace `YOURDOMAIN.com` there too, to match `nginx.conf` and `ALLOWED_HOSTS`.

---

## One-time server setup (Hostinger VPS)

1. **Point DNS at the server.** In Hostinger's DNS panel (or wherever the
   domain is registered), create an `A` record for `YOURDOMAIN.com` and
   `www.YOURDOMAIN.com` pointing at the VPS's public IP. Wait for
   propagation (`dig YOURDOMAIN.com` should return the right IP) before
   continuing — Certbot will fail otherwise.

2. **Install Docker + Compose** on the VPS if not already present:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   # log out and back in for the group change to apply
   ```

3. **Open firewall ports 80 and 443** (Hostinger VPS firewall panel, or
   `ufw`/`firewalld` on the box itself):
   ```bash
   sudo firewall-cmd --permanent --add-port=80/tcp
   sudo firewall-cmd --permanent --add-port=443/tcp
   sudo firewall-cmd --reload
   ```

4. **Clone the repo and create production `.env.prod`.** Never commit this
   file. Copy `.env.example` to `.env.prod` and set real values for:
   - `DEBUG=False`
   - `ALLOWED_HOSTS=YOURDOMAIN.com,www.YOURDOMAIN.com` (note: this key isn't
     in `.env.example` yet — add it by hand)
   - `DJANGO_SECRET_KEY=` — generate a fresh one, don't reuse the dev key
   - `POSTGRES_PASSWORD=` — a real password, not `change-me`
   - Any email/SMTP, Celery/Redis, and storage settings the app needs

---

## Resource limits (KVM1)

KVM1 has **4 GB RAM total**. Nothing in a bare compose file caps memory per
service, which is fine on a bigger box but risky here — an unbounded
Postgres or Redis under load can starve Gunicorn or Celery, and because
every service is `restart: unless-stopped`, an OOM kill shows up as a
mystery 502 with no obvious cause in the logs, not a clean crash.

`docker-compose.prod.yml` sets explicit `deploy.resources.limits.memory`
per service:

| Service | Limit | Notes |
|---|---|---|
| `web` (Gunicorn, 3 workers) | 1 GB | Watch this first if image uploads grow |
| `celery` | 300 MB | `--concurrency=2`, bumped down from unbounded |
| `db` (Postgres) | 512 MB | `shared_buffers=256MB`, `max_connections=50` |
| `redis` | 150 MB | `maxmemory 128mb`, `allkeys-lru` eviction |
| Nginx + certbot + host OS | ~500 MB | not containerized-limited, informal budget |

Total reserved: **~2.5 GB**, leaving ~1.5 GB headroom for traffic spikes and
Docker overhead. That headroom is comfortable at moderate load but not
infinite — see the swap note below as a second line of defense, and the
`docker stats` check in the post-deploy checklist.

If a service is consistently near its limit, it's a sign to either raise
that limit (and drop headroom elsewhere) or upgrade to KVM2 rather than
removing the limit entirely — removing it just moves the risk back to
"random OOM kill" instead of a visible, diagnosable constraint.

`postgres:16-alpine` and `redis:7-alpine` are used for smaller image size
and lower baseline memory — no functional change, skip if you rely on a
glibc-only extension.

---

## Swap (host-level safety net)

Memory limits above stop one runaway service from starving the others, but
don't prevent an OOM kill entirely if actual demand briefly exceeds 4 GB
(e.g. a `docker compose build` running alongside live traffic). A swapfile
turns that into "briefly slow" instead of "container killed":

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Verify with `free -h` — `Swap:` should show 2.0G total. This is a one-time
step per VPS, not per deploy.

---

## Firebase Admin SDK credentials

The service account JSON must never be committed to the repo or baked into
the Docker image (it would land in every image layer/registry, readable by
anyone with pull access). Instead, mount it read-only from the host:

```bash
mkdir -p /opt/eartha/secrets
# copy the downloaded service-account JSON to:
# /opt/eartha/secrets/firebase-adminsdk.json
chmod 600 /opt/eartha/secrets/firebase-adminsdk.json
```

`docker-compose.prod.yml` mounts it into both `web` and `celery` (add both
if any background task — e.g. push notifications — touches Firebase) and
sets `GOOGLE_APPLICATION_CREDENTIALS` to point at the mounted path. Add
`secrets/` to `.gitignore` on the server checkout if it isn't already.

Note: the application code (`apps/users/apps.py`) actually reads the
service-account JSON from the `FIREBASE_SERVICE_ACCOUNT_JSON` env var
(as a single-line JSON string), not from `GOOGLE_APPLICATION_CREDENTIALS`.
The file mount above is harmless to keep but currently redundant — as long
as `FIREBASE_SERVICE_ACCOUNT_JSON` is set in `.env.prod`, Firebase login
works regardless of the file mount.

---

## First deploy — bootstrapping the TLS certificate

Certbot can't issue a certificate until Nginx is running and reachable on
port 80, but Nginx's HTTPS block in `nginx.conf` won't start without a
certificate that doesn't exist yet. Two-step bootstrap:

**Step 1 — comment out the `server { listen 443 ... }` block** in
`nginx/nginx.conf` temporarily (or just don't paste it in yet), so only the
port-80 block exists. Then:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

**Step 2 — request the certificate:**
```bash
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d YOURDOMAIN.com -d www.YOURDOMAIN.com \
  --email you@youremail.com --agree-tos --no-eff-email
```

**Step 3 — restore the full `nginx.conf`** (with the 443 block back in),
then restart nginx so it picks up the new config:
```bash
docker compose -f docker-compose.prod.yml restart nginx
```

From here on, the `certbot` service's background loop handles renewal
automatically every 12 hours (checking, renewing only when due).

---

## Mostly fixed: `nginx` usually no longer needs a restart after rebuilding `web`

A bare `proxy_pass http://web:8000` resolves `web`'s address once, at
config load, and caches it for the life of the Nginx worker process. If you
then rebuilt or restarted `web` (a new deploy, for example), Docker
assigned it a new internal IP — but Nginx kept sending traffic to the
*old* one until restarted, producing a `502 Bad Gateway` in its logs
pointing at a stale IP. This bit us twice during testing — once between
`celery` and `redis`, once between `nginx` and `web` — same root cause
both times.

`nginx/nginx.conf` now routes through a variable with an explicit
`resolver 127.0.0.11 valid=10s` (Docker's embedded DNS), which forces
Nginx to re-resolve `web` every 10 seconds instead of once at startup.
Verified by repeatedly recreating `web` and `celery` together (the
realistic case — both are built from the same image, so a normal deploy
recreates both) and confirming Nginx picked up each new IP within
~10 seconds, no manual restart, across several clean runs — including a
run where `web` and `celery` happened to swap IPs with each other.

**This handles the normal deploy case — you shouldn't need to restart
`nginx` most of the time now.** A normal deploy is just:
```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

One caveat found during testing: once, after `web`+`celery` were rebuilt
together, Nginx got stuck resolving `web` to `celery`'s IP for several
minutes straight — longer than the 10s window should allow — most likely
a transient inconsistency in Docker's embedded DNS during that specific
container churn, not something Nginx's config can fully guard against.
**If a 502 ever outlives ~30 seconds after a deploy, it's the same old
gotcha — just reload/restart Nginx and it clears immediately:**
```bash
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```
This should be rare now, not the routine step it used to be.

If you ever edit `nginx/nginx.conf` itself (not just redeploy `web`), you
still need that same reload for the config change to take effect — that
part hasn't changed.

---

## ⚠️ Gotcha: don't delete/recreate the static or media volumes casually

The `static_data` and `media_data` named volumes only get correct
permissions because the `Dockerfile` pre-creates those directories with the
right owner *before* the volume is first created and populated. If you ever
run `docker volume rm eartha_static_data eartha_media_data` and recreate
them, that's fine — the fix is baked into the image now, permissions will
be correct again on the next `up`. But don't "clean up" that
`RUN mkdir -p /app/staticfiles /app/media` line in the Dockerfile thinking
it's redundant — without it, fresh volumes get created as `root`-owned and
the non-root `app` user inside the container gets a
`PermissionError: [Errno 13] Permission denied` trying to write static
files or uploads.

---

## Normal deploy from then on

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

No nginx restart needed (see the resolver fix above). Migrations and
`collectstatic` run automatically via the entrypoint script before
Gunicorn starts — no manual step needed either.

---

## Postgres backups

A volume is not a backup. Add a nightly cron job on the host:

```bash
# crontab -e
0 3 * * * docker exec $(docker compose -f /path/to/eartha/docker-compose.prod.yml ps -q db) \
  pg_dump -U eartha eartha | gzip > /home/YOURUSER/backups/eartha-$(date +\%F).sql.gz
```

Keep at least 7 days of rotation, and periodically copy backups off the VPS
(rsync to another machine, or upload to object storage) — a backup that
only lives on the same disk as the database doesn't protect against disk
failure.

If you ever need to recover from an old volume after a mistaken
`docker volume rm`, note that Docker won't actually delete a volume that's
still referenced by a running or stopped container under a *different*
compose project name — check `docker volume ls` for orphaned volumes named
after an old project before assuming data is gone.

---

## Post-deploy checklist

- [ ] `https://YOURDOMAIN.com` loads with a valid padlock, no mixed content
- [ ] `http://YOURDOMAIN.com` redirects to `https://`
- [ ] Static files (CSS/JS/admin styling) load correctly — if the page looks
      unstyled, check the static volume permissions gotcha above
- [ ] Uploaded images (e.g. benefit logos) load correctly from `/media/`
- [ ] Django admin login works without a CSRF error (confirms
      `CSRF_TRUSTED_ORIGINS` matches the real domain)
- [ ] `DEBUG=False` confirmed (visit a broken URL — should show a plain
      error page, not a stack trace)
- [ ] Celery worker logs show it connected to Redis and Postgres
- [ ] Cron backup job runs successfully once, and the `.sql.gz` file is valid
- [ ] After first real traffic, run `docker stats` for a few minutes and
      confirm no service is consistently pinned at its memory limit
- [ ] Confirm swap is active: `free -h` shows `Swap: 2.0G` total
- [ ] Confirm `web` and `celery` can read Firebase credentials (check logs
      for an Admin SDK initialization error on startup)
