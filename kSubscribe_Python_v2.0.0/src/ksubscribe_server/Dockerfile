FROM python:3.9-slim

# Install system dependencies including MariaDB connector
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libmariadb-dev \
    libmariadb-dev-compat \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy source code
COPY ./ksubscribe_share /app/ksubscribe_share      
COPY ./ksubscribe_server /app/ksubscribe_server   
COPY ./docker_collect /app/docker_collect
COPY ./docker_scraping /app/docker_scraping

# Create __init__.py files if they don't exist
RUN touch /app/ksubscribe_server/__init__.py
RUN touch /app/docker_collect/__init__.py
RUN touch /app/docker_scraping/__init__.py

# Install shared library first
RUN pip install --no-cache-dir /app/ksubscribe_share

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install FastAPI server dependencies
COPY ./ksubscribe_server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install additional dependencies if needed
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    python-jose[cryptography] \
    passlib[bcrypt] \
    aiofiles

# Set Python path
ENV PYTHONPATH=/app

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI server
CMD ["python", "-m", "uvicorn", "ksubscribe_server.fastApi.fastApi:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
