FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies and fonts for Brother label rendering with Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure data directory exists
RUN mkdir -p /app/data

# Expose port
EXPOSE 8085

# Run uvicorn with proxy headers enabled for reverse proxy identification
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085", "--proxy-headers", "--forwarded-allow-ips=*"]
