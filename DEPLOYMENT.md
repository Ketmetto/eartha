# Eartha — Production Deployment Guide

This covers what changed in `docker-compose.prod.yml`, why, and the steps to
actually go live on a Hostinger VPS. No CI/CD is set up yet — deploys are
manual (`git pull` + `docker compose up -d --build`). That's fine for launch;
revisit CI/CD later if deploys become frequent enough to be error-prone.

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

The app code and entrypoint script were already solid — migrations,
`collectstatic`, the non-root user, and the Postgres-readiness wait loop all
needed no changes.

---

## Files in this bundle

- `docker-compose.prod.yml` — replaces the existing one
- `nginx/nginx.conf` — reverse proxy + TLS termination + static/media serving

Copy both into the project root (keeping the `nginx/` subfolder), then edit
`nginx/nginx.conf` and replace every `YOURDOMAIN.com` with the real domain.

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

4. **Clone the repo and create production `.env`.** Never commit this file.
   Copy `.env.example` to `.env` and set real values for:
   - `DEBUG=False`
   - `ALLOWED_HOSTS=YOURDOMAIN.com,www.YOURDOMAIN.com`
   - `DJANGO_SECRET_KEY=` — generate a fresh one, don't reuse the dev key
     (`python -c "import secrets; print(secrets.token_urlsafe(50))"`)
   - `POSTGRES_PASSWORD=` — a real password, not `change-me`
   - `FIREBASE_SERVICE_ACCOUNT_JSON=` — the service-account key from the
     Firebase console, minified to a single line (needed for Google/Apple
     login; delivered as an env var, not a mounted file — see the Firebase
     note under "Resource limits" below)
   - Any email/SMTP, Celery/Redis, and storage settings the app needs

5. **Set up swap** (one-time, host-level — see "Resource limits" below for
   why this matters on a 4 GB box):
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
per service — nothing capped this before, which is fine on a bigger box
but risky here: an unbounded Postgres or Redis under load can starve
Gunicorn or Celery, and because every service is `restart: unless-stopped`,
an OOM kill shows up as a mystery 502 with no obvious cause in the logs,
not a clean crash.

| Service | Limit | Notes |
|---|---|---|
| `web` (Gunicorn, 3 workers) | 1 GB | Watch this first if image uploads grow |
| `celery` | 300 MB | `--concurrency=2` |
| `db` (Postgres) | 512 MB | `shared_buffers=256MB`, `max_connections=50` |
| `redis` | 150 MB | `maxmemory 128mb`, `allkeys-lru` eviction |
| Nginx + certbot + host OS | ~500 MB | not containerized-limited, informal budget |

Total reserved: **~2.5 GB**, leaving ~1.5 GB headroom for traffic spikes
and Docker overhead — comfortable at moderate load but not infinite. If a
service is consistently near its limit, raise that limit (and drop
headroom elsewhere) or upgrade to KVM2, rather than removing the limit
entirely — removing it just moves the risk back to "random OOM kill"
instead of a visible, diagnosable constraint. The swap step above is a
second line of defense for brief spikes above 4 GB (e.g. a
`docker compose build` running alongside live traffic), not a substitute
for right-sizing these limits.

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

## ⚠️ Gotcha: restart `nginx` after rebuilding `web` or `celery`

Nginx resolves `web`'s address once and caches it for the life of the
process. If you rebuild or restart `web` (a new deploy, for example),
Docker assigns it a new internal IP — but Nginx keeps trying the *old* one
until it's restarted, producing a `502 Bad Gateway` with a
`connect() failed (111: Connection refused)` error in its logs pointing at
a stale IP.

**Whenever you redeploy, restart nginx too:**
```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml restart nginx
```
Or just restart everything at once to avoid thinking about it:
```bash
docker compose -f docker-compose.prod.yml restart
```

This bit us twice during testing — once between `celery` and `redis`, once
between `nginx` and `web` — same root cause both times.

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
docker compose -f docker-compose.prod.yml restart nginx
```

Migrations and `collectstatic` run automatically via the entrypoint script
before Gunicorn starts — no manual step needed.

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
- [ ] Google/Apple login works (confirms `FIREBASE_SERVICE_ACCOUNT_JSON`
      parsed correctly — check `web`/`celery` logs for an Admin SDK
      initialization error otherwise)
- [ ] Swap is active: `free -h` shows `Swap: 2.0G` total
- [ ] After first real traffic, `docker stats` for a few minutes and
      confirm no service is consistently pinned at its memory limit
- [ ] Cron backup job runs successfully once, and the `.sql.gz` file is valid
