#!/bin/sh
set -e

# Wait for MySQL to be ready (if MYSQL_HOST is set)
if [ -n "$MYSQL_HOST" ]; then
    echo "Waiting for MySQL at $MYSQL_HOST:${MYSQL_PORT:-3306}..."

    # Build connection string for Flyway
    FLYWAY_URL="jdbc:mysql://${MYSQL_HOST}:${MYSQL_PORT:-3306}/${MYSQL_DATABASE}"

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

    # Run Flyway migrations
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
