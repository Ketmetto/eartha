# Django + Docker + Nginx + Redis + Postgres + Firebase — Hostinger KVM1 Deployment Plan

Target: Hostinger VPS KVM1 (4 GB RAM, 50 GB NVMe, 4 TB bandwidth). Tight but workable for a single Django app.

## Architecture

```
Internet → Nginx (host, SSL termination) → Docker network
                                              ├── django (gunicorn, internal)
                                              ├── postgres
                                              ├── redis (cache + celery broker)
                                              └── celery worker/beat (if needed)
Firebase: external (Admin SDK from Django — Auth/FCM/Storage, not self-hosted)
```

Nginx runs on the **host** (not in Docker) so it can act as the SSL/reverse-proxy layer for future apps on the same VPS without extra container networking. Everything else stays in Compose.

## 1. VPS provisioning

```bash
# Hostinger: order KVM1, choose Ubuntu 24.04 LTS (better Docker repo support than Fedora on VPS)
ssh root@<ip>
adduser deploy && usermod -aG sudo deploy
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
# Disable root SSH login + password auth after key-based access is confirmed
```

## 2. Docker install

```bash
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
apt install docker-compose-plugin -y
```

## 3. Repo layout on server

```
/opt/eartha/
├── docker-compose.prod.yml
├── .env.prod            # not in git
├── nginx/
│   └── eartha.conf
└── app/                 # git pull of your Django repo
```

## 4. docker-compose.prod.yml — resource-conscious for 4 GB RAM

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    volumes: ["pgdata:/var/lib/postgresql/data"]
    env_file: .env.prod
    command: postgres -c shared_buffers=256MB -c max_connections=50
    deploy:
      resources: { limits: { memory: 512M } }

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
    deploy:
      resources: { limits: { memory: 150M } }

  django:
    build: ./app
    restart: unless-stopped
    env_file: .env.prod
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --threads 2
    depends_on: [db, redis]
    volumes: ["static:/app/staticfiles", "media:/app/media"]
    ports: ["127.0.0.1:8000:8000"]
    deploy:
      resources: { limits: { memory: 1G } }

  celery:
    build: ./app
    restart: unless-stopped
    env_file: .env.prod
    command: celery -A config worker -l info --concurrency=2
    depends_on: [db, redis]
    deploy:
      resources: { limits: { memory: 300M } }

volumes: { pgdata: {}, static: {}, media: {} }
```

Notes:
- Gunicorn worker formula is `(2×cores)+1`. KVM1 usually has 1–2 vCPU, so 3 workers is appropriate.
- Skip a separate `celery beat` container unless you have scheduled tasks — merge with the worker via the `-B` flag to save RAM if not needed.
- Bind Django's port to `127.0.0.1:8000` only (not `0.0.0.0`) since Nginx on the host is the public entry point.

## 5. Nginx (host-level) — `/etc/nginx/sites-available/eartha`

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location /static/ { alias /opt/eartha/staticfiles/; }
    location /media/  { alias /opt/eartha/media/; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then enable SSL:

```bash
certbot --nginx -d api.yourdomain.com
```

## 6. Django settings for production

- `DEBUG=False`, `ALLOWED_HOSTS` sourced from env
- `django-storages` if media should go to an S3-compatible bucket instead of local disk (saves the 50 GB NVMe allocation)
- `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`
- Firebase Admin SDK: store the service account JSON as a Docker secret or mount it read-only, load via `GOOGLE_APPLICATION_CREDENTIALS` env var — never bake it into the image

## 7. Deploy flow

```bash
cd /opt/eartha
git pull origin main
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm django python manage.py migrate
docker compose -f docker-compose.prod.yml run --rm django python manage.py collectstatic --noinput
docker compose -f docker-compose.prod.yml up -d
```

Wrap this in a `deploy.sh` on the server, or a GitHub Actions job that SSHs in and runs it on push to `main`.

## 8. Backups

```bash
# cron: nightly pg_dump to a separate volume + rotate
0 3 * * * docker exec eartha-db-1 pg_dump -U eartha_user eartha > /opt/backups/eartha-$(date +\%F).sql
```

Push these off-box (e.g. rclone to Backblaze/S3) — Hostinger does not snapshot Docker volumes automatically.

## Memory budget check (4 GB total)

| Service | Limit |
|---|---|
| Postgres | 512 MB |
| Redis | 150 MB |
| Django (gunicorn) | 1 GB |
| Celery worker | 300 MB |
| Host OS + Nginx | ~500 MB |
| **Total** | **~2.5 GB** |

Leaves headroom for traffic spikes and Docker overhead. Comfortable for KVM1 at moderate load; if the Submissions app starts handling image uploads at volume, watch Django worker memory first — that's the most likely place to hit limits.

## Possible next steps

- Multi-stage, non-root-user Dockerfile for the `app/` build
- GitHub Actions deploy workflow (SSH + `deploy.sh` trigger on push to `main`)
