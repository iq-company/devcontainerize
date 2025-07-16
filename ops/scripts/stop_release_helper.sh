#!/bin/bash

# This script is a helper for the 'make stop-release' target.
# It stops the docker compose services, respecting the .env.release file if it exists.

set -e

# Define potential .env file paths
DEFAULT_ENV_FILE="./ops/compose/.env"
RELEASE_ENV_FILE="./ops/compose/.env.release"

# Determine which .env file to use as the source of truth
ENV_FILE_PATH="$DEFAULT_ENV_FILE"
if [ -f "$RELEASE_ENV_FILE" ]; then
    echo "Using release-specific environment file: $RELEASE_ENV_FILE"
    ENV_FILE_PATH="$RELEASE_ENV_FILE"
else
    echo "Using default environment file: $DEFAULT_ENV_FILE"
fi

if [ ! -f "$ENV_FILE_PATH" ]; then
    echo "Warning: Environment file not found at $ENV_FILE_PATH. Cannot determine project name. Attempting to stop without it."
    docker compose --project-directory ./ops/compose down
    exit 0
fi

# Determine PROJECT_NAME from the chosen .env file
PROJECT_NAME=$(awk -F= '/^COMPOSE_PROJECT_NAME=/ {print $2}' "$ENV_FILE_PATH" | xargs)

echo "Stopping docker-compose project: $PROJECT_NAME..."

docker compose -p "$PROJECT_NAME" --project-directory ./ops/compose down