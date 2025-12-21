#!/bin/sh
set -e

# Wait for MySQL to be ready (if MYSQL_HOST is set)
if [ -n "$MYSQL_HOST" ]; then
    echo "Waiting for MySQL at $MYSQL_HOST:${MYSQL_PORT:-3306}..."

    # Build connection string for Flyway (allowPublicKeyRetrieval needed for MySQL 8.0 caching_sha2_password auth)
    FLYWAY_URL="jdbc:mysql://${MYSQL_HOST}:${MYSQL_PORT:-3306}/${MYSQL_DATABASE}?allowPublicKeyRetrieval=true&useSSL=false"

    # Wait up to 60 seconds for MySQL
    timeout=60
    while [ $timeout -gt 0 ]; do
        if nc -z "$MYSQL_HOST" "${MYSQL_PORT:-3306}" 2>/dev/null; then
            echo "MySQL is available"
            break
        fi
        echo "Waiting for MySQL... ($timeout seconds remaining)"
        sleep 1
        timeout=$((timeout - 1))
    done

    if [ $timeout -eq 0 ]; then
        echo "ERROR: MySQL did not become available in time"
        exit 1
    fi

    # Run Flyway repair first to clean up any failed migration records
    # This is safe to run even if there are no failed migrations
    echo "Running Flyway repair (cleans up failed migration records)..."
    flyway \
        -url="$FLYWAY_URL" \
        -user="$MYSQL_USER" \
        -password="$MYSQL_PASSWORD" \
        -locations="filesystem:/app/sql" \
        -connectRetries=3 \
        repair || true

    # Run Flyway migrations
    # All migrations (V3, V9, etc.) are now idempotent - they check if columns exist
    # before adding them, so they're safe to run even if schema already has the columns
    echo "Running Flyway migrations..."
    flyway \
        -url="$FLYWAY_URL" \
        -user="$MYSQL_USER" \
        -password="$MYSQL_PASSWORD" \
        -locations="filesystem:/app/sql" \
        -connectRetries=3 \
        migrate

    echo "Flyway migrations completed successfully"
else
    echo "MYSQL_HOST not set, skipping Flyway migrations"
fi

# Execute the main application
echo "Starting application..."
exec "$@"
