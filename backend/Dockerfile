# Backend image for Render / Railway / any container host.
FROM python:3.12-slim

# Fail fast and log immediately rather than buffering output, so a crash loop
# in production shows its reason.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libpq is needed by psycopg for Alembic migrations.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user. A container compromise should not also be root.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# The host's load balancer checks this; a failed database connection surfaces
# as "not ready" rather than a restart loop.
#
# The port must come from $PORT, not a literal: Render (and most container
# hosts) assign the port at run time, so a hardcoded 8000 would probe a port
# nothing is listening on and report a healthy container as unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/api/v1/health" || exit 1

# Migrations run at start-up so a deploy cannot serve a schema it does not
# match. If the migration fails the container refuses to start, which is the
# correct outcome.
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'
