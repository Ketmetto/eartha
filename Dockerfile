FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

ARG INSTALL_EXTRA=dev
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[${INSTALL_EXTRA}]"

COPY . .

RUN chmod +x scripts/entrypoint.sh

# Run as a non-root, host-UID-matched user so files the container writes
# into the bind-mounted ./:/app dev volume (media/, staticfiles/,
# __pycache__) come out owned by you on the host instead of root. Override
# APP_UID/APP_GID at build time if your host user isn't the common default
# 1000 (check with `id -u`/`id -g`); in Compose that's the `build.args` for
# each service. Only matters for the bind-mount case (dev) — the prod
# compose file has no volume, so the chown below is what actually sticks.
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd -g "${APP_GID}" app && useradd -u "${APP_UID}" -g app -M app \
    && chown -R app:app /app
USER app

ENTRYPOINT ["scripts/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
