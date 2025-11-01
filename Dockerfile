FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Upgrade pip and configure for better network resilience
RUN pip install --upgrade pip setuptools wheel

# Install large scientific packages first with retries and longer timeout
RUN pip install --no-cache-dir --timeout=300 --retries=5 \
    numpy>=1.21.0 \
    scipy>=1.7.0 \
    matplotlib>=3.7.0

# Install remaining requirements
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt

# Install ell-ai separately
RUN pip install --timeout=300 --retries=5 -U "ell-ai[all]"

# Copy the entire application
COPY . .

ENV GMAIL_EMAIL=""
ENV GMAIL_PASSWORD=""
ENV PYTHONUNBUFFERED=1

# Default to running the API service
CMD ["python", "api_service.py"]
