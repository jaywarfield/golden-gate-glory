# Dockerfile
# Golden Gate Glory – Veteran Career Navigator  (Phase 1 web front-end)
#
# OpenShift-compatible:
#   - Runs as non-root user (UID 1001) to satisfy OpenShift's restricted SCC.
#   - Listens on port 8080 (non-privileged).
#   - Gunicorn is used as the production WSGI server.
#
# Build:
#   docker build -t golden-gate-glory-web:latest .
#
# Run locally:
#   docker run --rm -p 8080:8080 \
#     -e ORCHESTRATE_ENDPOINT="https://..." \
#     -e ORCHESTRATE_API_KEY="..." \
#     -e USE_MOCK="false" \
#     golden-gate-glory-web:latest

# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY web/requirements.txt .

RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.11-slim

# OpenShift runs containers with a random UID in group 0 by default.
# Creating a named user (UID 1001) and making /app group-writable
# satisfies both standard Docker and OpenShift restricted SCC.
RUN groupadd -g 1001 appgroup \
 && useradd -u 1001 -g appgroup -s /sbin/nologin appuser \
 && mkdir -p /app \
 && chown -R 1001:0 /app \
 && chmod -R g=u /app

# Copy pre-built packages from the builder stage
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy only the web sub-package (app.py + templates/)
COPY web/app.py        ./app.py
COPY web/templates/    ./templates/

USER 1001

EXPOSE 8080

# Gunicorn: 2 workers, bind to 0.0.0.0:8080
# Adjust --workers based on available CPU (formula: 2 * nCPU + 1)
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "app:app"]
