#!/bin/bash

# This script is a helper for running release environments.
# Usage: ./run_release_helper.sh [stage_name]
#   stage_name: e.g., "local", "staging", "prod" (default: dev)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$SCRIPT_DIR/../../compose"

# Determine stage (default: dev)
STAGE_NAME="${1:-dev}"

# Load env vars via cascade (shared + stage)
source "$SCRIPT_DIR/../common/load_env.sh" "$STAGE_NAME"

echo "Stage: $STAGE_NAME"
echo "DBMS: $DBMS"
echo "Project: $COMPOSE_PROJECT_NAME"

# Validate DBMS
if [[ "$DBMS" != "postgres" && "$DBMS" != "mariadb" && "$DBMS" != "sqlite" ]]; then
    echo "Error: Invalid DBMS '$DBMS'"
    exit 1
fi

# Ensure init_site.sh is executable
chmod +x "$SCRIPT_DIR/../runtime/init_site.sh" 2>/dev/null || true

# Build compose file list based on DBMS
COMPOSE_FILES="-f $COMPOSE_DIR/compose.base.yml"
if [ "$DBMS" != "sqlite" ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f $COMPOSE_DIR/compose.$DBMS.yml"
    if [ -f "$COMPOSE_DIR/compose.init.$DBMS.yml" ]; then
        COMPOSE_FILES="$COMPOSE_FILES -f $COMPOSE_DIR/compose.init.$DBMS.yml"
    fi
fi
COMPOSE_FILES="$COMPOSE_FILES -f $COMPOSE_DIR/compose.release.yml"

# Build env-file args (shared first, then stage-specific override)
ENV_FILE_ARGS="--env-file $COMPOSE_DIR/.env --env-file $COMPOSE_DIR/.env.$STAGE_NAME"

echo "Starting docker compose..."
docker compose -p "$COMPOSE_PROJECT_NAME" \
    $ENV_FILE_ARGS \
    $COMPOSE_FILES \
    --project-directory "$COMPOSE_DIR" \
    up --remove-orphans
