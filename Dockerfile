# Dockerfile for Oracle Cloud deployment
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY app_main.py .
COPY templates/ ./templates/
COPY training/ ./training/

# Copy model artifacts if they exist (optional — train on first run if not present)
COPY artifacts/ ./artifacts/

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8080

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "app_main:app"]
