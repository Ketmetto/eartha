FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Gunicorn's control-socket falls back to $HOME/.gunicorn/, which doesn't
# exist for the -M (no home dir) `app` user below — point it at /tmp instead.
ENV XDG_RUNTIME_DIR=/tmp

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

# Non-root, host-UID-matched user so files written into the bind-mounted
# dev volume come out owned by you, not root. Override APP_UID/APP_GID at
# build time if your host user isn't the default 1000 (`id -u`/`id -g`).
ARG APP_UID=1000
ARG APP_GID=1000
RUN mkdir -p /app/staticfiles /app/media \
    && groupadd -g "${APP_GID}" app && useradd -u "${APP_UID}" -g app -M app \
    && chown -R app:app /app
USER app

ENTRYPOINT ["scripts/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
