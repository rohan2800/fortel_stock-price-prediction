# Multi-stage Dockerfile for Fortel Flask app

# Builder stage: install build deps and build wheels
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Install build-time system deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and build wheels into /wheels
COPY requirements.txt ./
RUN pip install --upgrade pip wheel setuptools \
    && pip wheel --wheel-dir=/wheels -r requirements.txt

# Runtime stage: smaller image with only runtime deps
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Minimal runtime system libraries (keep small)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgcc1 \
    && rm -rf /var/lib/apt/lists/*

# Copy built wheels from builder and install without rebuilding
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Copy the application code (Dockerfile .dockerignore excludes large artifacts)
COPY . .

# Create an unprivileged user and fix permissions
RUN useradd -m appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 5000

# Use gunicorn for production-like server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "--workers", "2"]
