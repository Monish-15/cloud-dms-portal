# Multi-stage production Dockerfile for Secure Document Management Portal
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies and install into wheelhouse
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt gunicorn==23.0.0

# ----------------- Runtime Stage -----------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user for principle of least privilege
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Install wheels from builder stage
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application source code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY run.py .
COPY pyproject.toml .

# Create uploads directory and assign ownership
RUN mkdir -p uploads && chown -R appuser:appgroup /app

USER appuser

ENV FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    LOCAL_UPLOAD_FOLDER=/app/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/login')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
