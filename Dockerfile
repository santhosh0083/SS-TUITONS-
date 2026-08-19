# Backend image, built from the REPOSITORY ROOT.
#
# Why this exists when backend/Dockerfile already does:
#
# Render's service for this API was created as a plain Web Service rather than
# from render.yaml, so it never reads that file -- it uses its own saved
# settings, which are the defaults: Dockerfile Path "./Dockerfile", build
# context = repo root. Four builds failed with
#     failed to read dockerfile: open Dockerfile: no such file or directory
# because the only Dockerfile lived in backend/.
#
# Rather than depend on someone correcting three dashboard fields, this file
# sits exactly where the default setting already looks. backend/Dockerfile is
# kept for local builds and for hosts pointed at that directory; the two stay
# in step because both install the same requirements and run the same command.

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

# Dependencies first: this layer is cached until requirements.txt changes.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the backend is copied. The frontend is deployed separately on Vercel and
# has no business in this image.
COPY backend/ .

# Run as a non-root user. A container compromise should not also be root.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# The port comes from $PORT, which the host assigns at run time.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/api/v1/health" || exit 1

# Migrations run at start-up so a deploy cannot serve a schema it does not
# match. If the migration fails the container refuses to start, which is the
# correct outcome.
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'
