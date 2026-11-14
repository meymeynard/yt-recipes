# ----------------------------------------------------
# Dockerfile for Pantry Chef (YouTube Recipe Aggregator)
# ----------------------------------------------------
FROM python:3.11-slim

# Prevent Python from writing .pyc and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8501 \
    DB_PATH=/app/data/recipes.db

WORKDIR /app

# Install system dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -m -s /bin/bash appuser

# Install Python dependencies separately for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create data directory and set permissions for non-root user
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Copy application source code
COPY --chown=appuser:appuser . .

# Ensure data directory ownership
RUN chown -R appuser:appuser /app/data

# Switch to non-root user
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/health || exit 1

ENTRYPOINT ["python", "app.py"]
