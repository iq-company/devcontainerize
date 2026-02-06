#!/bin/bash

# Stop release environment containers
# Usage: ./stop_release_helper.sh [stage_name]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE_NAME="${1:-dev}"

# Load env vars via cascade (shared + stage)
source "$SCRIPT_DIR/../common/load_env.sh" "$STAGE_NAME"

echo "Stopping project: $COMPOSE_PROJECT_NAME..."
docker compose -p "$COMPOSE_PROJECT_NAME" down --remove-orphans
echo "✅ Stopped."
