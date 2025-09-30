FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -U "ell-ai[all]"

COPY gmail_fetcher.py domain_service.py remote_sqlite_helper.py credentials_service.py ./

ENV GMAIL_EMAIL=""
ENV GMAIL_PASSWORD=""
ENV CREDENTIALS_DB_PATH="/app/credentials.db"
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "gmail_fetcher.py"]
