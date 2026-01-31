#!/bin/bash

# This script is a helper for the 'make run-release' target.
# It handles the logic for determining the DBMS and running docker compose.
# It accepts an optional path to an env file as the first argument.

set -e

# Define potential .env file paths
DEFAULT_ENV_FILE="./ops/compose/.env"
RELEASE_ENV_FILE="./ops/compose/.env.release"
CUSTOM_ENV_FILE=$1

# Determine which .env file to use
if [ -n "$CUSTOM_ENV_FILE" ] && [ -f "$CUSTOM_ENV_FILE" ]; then
    echo "Using custom environment file: $CUSTOM_ENV_FILE"
    ENV_FILE_PATH="$CUSTOM_ENV_FILE"
    # The --env-file flag is crucial to make Docker Compose use it for interpolation
    ENV_FILE_ARG="--env-file $CUSTOM_ENV_FILE"
elif [ -f "$RELEASE_ENV_FILE" ]; then
    echo "Using release-specific environment file: $RELEASE_ENV_FILE"
    ENV_FILE_PATH="$RELEASE_ENV_FILE"
    ENV_FILE_ARG="--env-file $RELEASE_ENV_FILE"
else
    echo "Using default environment file: $DEFAULT_ENV_FILE"
    ENV_FILE_PATH="$DEFAULT_ENV_FILE"
    # When using the default, this arg is not needed, as Compose finds it automatically
    ENV_FILE_ARG=""
fi

# Ensure the chosen .env file exists, or create the default one
if [ ! -f "$ENV_FILE_PATH" ]; then
	if [ "$ENV_FILE_PATH" = "$DEFAULT_ENV_FILE" ]; then
		echo "Default .env file not found, running init script to create it..."
		bash ./ops/scripts/devcontainer/init_env_files
	else
		# This case should not be reached due to the check above, but is good for safety
		echo "Error: Release env file was specified but not found at $RELEASE_ENV_FILE"
		exit 1
	fi
fi

# Ensure init_site.sh is executable
chmod +x ./ops/scripts/runtime/init_site.sh

# Determine DBMS from the chosen .env file
DBMS=$(awk -F= '/^DBMS=/ {print $2}' "$ENV_FILE_PATH" | xargs)
echo "Using DBMS: [$DBMS]"

# Validate DBMS
if [[ "$DBMS" != "postgres" && "$DBMS" != "mariadb" && "$DBMS" != "sqlite" ]]; then
	echo "Error: Invalid DBMS '$DBMS' detected in $ENV_FILE_PATH file."
	exit 1
fi

# Determine PROJECT_NAME from the chosen .env file
PROJECT_NAME=$(awk -F= '/^COMPOSE_PROJECT_NAME=/ {print $2}' "$ENV_FILE_PATH" | xargs)
echo "Starting docker-compose with project name: $PROJECT_NAME..."

# Build compose file list based on DBMS
COMPOSE_FILES="-f ./ops/compose/compose.base.yml"
if [ "$DBMS" != "sqlite" ]; then
	COMPOSE_FILES="$COMPOSE_FILES -f ./ops/compose/compose.$DBMS.yml"
	if [ -f "./ops/compose/compose.init.$DBMS.yml" ]; then
		COMPOSE_FILES="$COMPOSE_FILES -f ./ops/compose/compose.init.$DBMS.yml"
	fi
fi
COMPOSE_FILES="$COMPOSE_FILES -f ./ops/compose/compose.release.yml"

docker compose -p "$PROJECT_NAME" \
	$ENV_FILE_ARG \
	$COMPOSE_FILES \
	--project-directory ./ops/compose \
	up --remove-orphans
