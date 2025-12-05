FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including tini, netcat, and Java (required for Flyway)
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    tini \
    netcat-openbsd \
    wget \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Install Flyway
ENV FLYWAY_VERSION=10.10.0
RUN wget -qO- https://repo1.maven.org/maven2/org/flywaydb/flyway-commandline/${FLYWAY_VERSION}/flyway-commandline-${FLYWAY_VERSION}-linux-x64.tar.gz | tar xz \
    && mv flyway-${FLYWAY_VERSION} /opt/flyway \
    && ln -s /opt/flyway/flyway /usr/local/bin/flyway

COPY requirements.txt .

# Upgrade pip and configure for better network resilience
RUN pip install --upgrade pip setuptools wheel

# Install all requirements with retries and longer timeout for network resilience
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt

# Install ell-ai separately
RUN pip install --timeout=300 --retries=5 -U "ell-ai[all]"

# Copy the entire application
COPY . .

# Copy SQL migrations
COPY sql/ /app/sql/

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV GMAIL_EMAIL=""
ENV GMAIL_PASSWORD=""
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH="/app/email_summaries/summaries.db"

# Use tini as init system, entrypoint handles Flyway then exec's the command
ENTRYPOINT ["/usr/bin/tini", "--", "/docker-entrypoint.sh"]

# Default to running the API service
CMD ["python", "api_service.py"]
