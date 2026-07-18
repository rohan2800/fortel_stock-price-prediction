# Dockerfile for Fortel Flask app
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# system deps for any packages that need compilation
RUN apt-get update && apt-get install -y build-essential --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . .

# Expose port
EXPOSE 5000

# Use gunicorn for production-like server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "--workers", "4"]
