FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -U "ell-ai[all]"

# Copy the entire application
COPY . .

ENV GMAIL_EMAIL=""
ENV GMAIL_PASSWORD=""
ENV PYTHONUNBUFFERED=1

# Default to running the API service
CMD ["python", "api_service.py"]
