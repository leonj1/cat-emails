FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Upgrade pip and configure for better network resilience
RUN pip install --upgrade pip setuptools wheel

# Install all requirements with retries and longer timeout for network resilience
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt

# Install ell-ai separately
RUN pip install --timeout=300 --retries=5 -U "ell-ai[all]"

# Copy the entire application
COPY . .

ENV GMAIL_EMAIL=""
ENV GMAIL_PASSWORD=""
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH="/app/email_summaries/summaries.db"

# Default to running the API service
CMD ["python", "api_service.py"]
