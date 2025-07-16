#!/bin/bash

# This script is a helper for the 'make clean-release' target.
# It stops and removes docker compose services, volumes, and networks,
# respecting the .env.release file if it exists.

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
    echo "Warning: Environment file not found at $ENV_FILE_PATH. Cannot determine project name. Attempting to clean without it."
    docker compose --project-directory ./ops/compose down --remove-orphans
    exit 0
fi

# Determine PROJECT_NAME from the chosen .env file
PROJECT_NAME=$(awk -F= '/^COMPOSE_PROJECT_NAME=/ {print $2}' "$ENV_FILE_PATH" | xargs)

echo "Stopping and removing containers for project: $PROJECT_NAME..."

# Always run down without --volumes first to stop containers
docker compose -p "$PROJECT_NAME" --project-directory ./ops/compose down --remove-orphans

# Ask the user if they also want to remove the volumes
read -p "Do you also want to remove the persistent volumes (THIS WILL DELETE THE DATABASE)? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing volumes for project: $PROJECT_NAME..."
    docker compose -p "$PROJECT_NAME" --project-directory ./ops/compose down --volumes --remove-orphans
fi

echo "Cleanup complete."
