FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt setup.py ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -U "ell-ai[all]"

COPY cat_emails/ ./cat_emails/
RUN pip install -e .

ENV GMAIL_EMAIL=""
ENV GMAIL_PASSWORD=""
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "cat_emails.gmail_fetcher"]
