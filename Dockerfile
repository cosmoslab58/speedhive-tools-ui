FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
COPY speedhive-tools ./speedhive-tools
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user. uid/gid 1000 on purpose: it is nathan on bodhi,
# the owner of the bind-mounted ./data (see docker-compose.yml), which the app
# writes (per-org settings, caches, dumps). Temp files go to /tmp; gunicorn
# needs a writable home for its control socket, hence --create-home.
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin app
USER 1000:1000

EXPOSE 8854

# Single worker so the in-process org-analysis cache (app/analysis_cache.py,
# ~175MB per org) is shared by every request instead of duplicated per worker
CMD ["gunicorn", "--bind", "0.0.0.0:8854", "--workers", "1", "--worker-class", "gthread", "--threads", "8", "--timeout", "180", "--graceful-timeout", "30", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
