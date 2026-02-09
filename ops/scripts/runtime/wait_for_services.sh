#!/bin/bash
# =============================================================================
# Wait for external services (DB, Redis) to be available
# =============================================================================
# Called by: init_site.sh, compose.init.wait.yml
#
# Uses wait-for-it to check service availability.
# Works for both container services and external services.

set -e

echo "Waiting for services..."

# Wait for database
# Skip if: no DB_HOST, or DB_HOST is a file path (starts with / or .)
if [ -n "$DB_HOST" ] && [[ ! "$DB_HOST" =~ ^[./] ]]; then
    # Use default port if not specified
    if [ -z "$DB_PORT" ]; then
        case "$DBMS" in
            postgres) DB_PORT=5432 ;;
            mariadb)  DB_PORT=3306 ;;
            *)        DB_PORT="" ;;
        esac
    fi
    if [ -n "$DB_PORT" ]; then
        echo "  → Database at $DB_HOST:$DB_PORT..."
        wait-for-it "$DB_HOST:$DB_PORT" --timeout=900 --strict
    fi
fi

# Wait for Redis cache
if [ -n "$REDIS_CACHE" ]; then
    REDIS_HOST=$(echo "$REDIS_CACHE" | sed 's|redis://||' | cut -d: -f1)
    REDIS_PORT=$(echo "$REDIS_CACHE" | sed 's|redis://||' | cut -d: -f2 | cut -d/ -f1)
    if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
        echo "  → Redis cache at $REDIS_HOST:$REDIS_PORT..."
        wait-for-it "$REDIS_HOST:$REDIS_PORT" --timeout=300 --strict
    fi
fi

# Wait for Redis queue
if [ -n "$REDIS_QUEUE" ]; then
    REDIS_HOST=$(echo "$REDIS_QUEUE" | sed 's|redis://||' | cut -d: -f1)
    REDIS_PORT=$(echo "$REDIS_QUEUE" | sed 's|redis://||' | cut -d: -f2 | cut -d/ -f1)
    if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
        echo "  → Redis queue at $REDIS_HOST:$REDIS_PORT..."
        wait-for-it "$REDIS_HOST:$REDIS_PORT" --timeout=30 --strict
    fi
fi

echo "All services available."
