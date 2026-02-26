# Promptdis API — multi-stage build
# Build: podman build -t promptdis -f Containerfile .
#   (or: docker build -t promptdis .)

# ── Builder ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# ── Runtime ──────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY server/ server/

# Non-root user + data directory for SQLite
RUN useradd --create-home appuser && mkdir -p data && chown appuser:appuser data
USER appuser

EXPOSE 8000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
