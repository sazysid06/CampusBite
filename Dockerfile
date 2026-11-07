FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system build dependencies required for compiling packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and install packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application backend code, tests, and configurations
COPY backend/ ./backend/
COPY tests/ ./tests/
COPY pytest.ini .

# Create persistent storage directory for the SQLite database
RUN mkdir -p /app/data

# Expose FastAPI server port
EXPOSE 8000

# Start Uvicorn bound to 0.0.0.0
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]