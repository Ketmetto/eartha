# Eartha — Production Deployment Guide

This covers what changed in `docker-compose.prod.yml`, why, and the steps to
actually go live on a Hostinger VPS. No CI/CD is set up yet — deploys are
manual (`git pull` + `docker compose up -d --build`). That's fine for launch;
revisit CI/CD later if deploys become frequent enough to be error-prone.

---

## What was missing before, and what changed

| Gap | Fix |
|---|---|
| No TLS / HTTPS | Added `nginx` + `certbot` services |
| Gunicorn exposed directly on `:8000` | Changed `ports` → `expose`; only Nginx is reachable from the internet now |
| No persistent media storage | Added `media_data` volume, mounted into `web` and `celery` |
| No persistent static file serving | Added `static_data` volume, `collectstatic` writes here, Nginx serves it directly |
| No backup plan for Postgres | Documented below (cron + `pg_dump`) |

The app code, `Dockerfile`, and entrypoint script were already solid —
migrations, `collectstatic`, non-root user, and the Postgres-readiness wait
loop all needed no changes.

---

## Files in this bundle

- `docker-compose.prod.yml` — replaces your current one
- `nginx/nginx.conf` — reverse proxy + TLS termination + static/media serving

Copy both into your project root (keeping the `nginx/` subfolder), then edit
`nginx/nginx.conf` and replace every `YOURDOMAIN.com` with your real domain.

---

## One-time server setup (Hostinger VPS)

1. **Point DNS at the server.** In Hostinger's DNS panel (or wherever your
   domain is registered), create an `A` record for `YOURDOMAIN.com` and
   `www.YOURDOMAIN.com` pointing at your VPS's public IP. Wait for
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

4. **Clone the repo and add production `.env`.** Never commit this file.
   Required values to set for real (not dev defaults):
   - `DEBUG=False`
   - `ALLOWED_HOSTS=YOURDOMAIN.com,www.YOURDOMAIN.com`
   - `SECRET_KEY=` — generate a fresh one, don't reuse the dev key
   - `POSTGRES_PASSWORD=` — a real password, not `change-me`
   - Any email/SMTP, Celery/Redis, and storage settings your app needs

---

## First deploy — bootstrapping the TLS certificate

Certbot can't issue a certificate until Nginx is running and reachable on
port 80, but Nginx's HTTPS block in `nginx.conf` won't start without a
certificate that doesn't exist yet. Two-step bootstrap:

**Step 1 — comment out the `server { listen 443 ... }` block** in
`nginx/nginx.conf` temporarily (or just don't paste it in yet), so only the
port-80 block exists. Then:

```bash
docker compose -f docker-compose.prod.yml up -d nginx web db redis celery
```

**Step 2 — request the certificate:**
```bash
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d YOURDOMAIN.com -d www.YOURDOMAIN.com \
  --email you@youremail.com --agree-tos --no-eff-email
```

**Step 3 — restore the full `nginx.conf`** (with the 443 block back in),
then reload:
```bash
docker compose -f docker-compose.prod.yml restart nginx
```

From here on, the `certbot` service's background loop handles renewal
automatically every 12 hours (checking, renewing only when due).

---

## Normal deploy from then on

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
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

---

## Post-deploy checklist

- [ ] `https://YOURDOMAIN.com` loads with a valid padlock, no mixed content
- [ ] `http://YOURDOMAIN.com` redirects to `https://`
- [ ] Static files (CSS/JS/admin styling) load correctly
- [ ] Uploaded images (e.g. benefit logos) load correctly from `/media/`
- [ ] Django admin login works, `DEBUG=False` confirmed (visit a broken URL —
      you should see a plain error page, not a stack trace)
- [ ] Celery worker logs show it connected to Redis and Postgres
- [ ] Cron backup job runs successfully once, and the `.sql.gz` file is valid
