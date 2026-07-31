# Addendum: Resource limits, swap, and Firebase creds (Hostinger KVM1)

Insert this section into `DEPLOYMENT.md` — suggested placement is right
after "One-time server setup" and before "First deploy — bootstrapping the
TLS certificate."

---

## Resource limits (KVM1)

KVM1 has **4 GB RAM total**. Nothing in the original compose file capped
memory per service, which is fine on a bigger box but risky here — an
unbounded Postgres or Redis under load can starve Gunicorn or Celery, and
because every service is `restart: unless-stopped`, an OOM kill shows up
as a mystery 502 with no obvious cause in the logs, not a clean crash.

`docker-compose.prod.yml` now sets explicit `deploy.resources.limits.memory`
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

Switched `postgres:16` → `postgres:16-alpine` and `redis:7` → `redis:7-alpine`
for smaller image size and lower baseline memory — no functional change,
skip if you rely on a glibc-only extension.

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

---

## Post-deploy checklist addition

- [ ] After first real traffic, run `docker stats` for a few minutes and
      confirm no service is consistently pinned at its memory limit
- [ ] Confirm swap is active: `free -h` shows `Swap: 2.0G` total
- [ ] Confirm `web` and `celery` can read Firebase credentials (check logs
      for an Admin SDK initialization error on startup)
