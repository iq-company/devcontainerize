#!/bin/bash

# Clean release environment (containers, volumes, networks)
# Usage: ./clean_release_helper.sh [stage_name]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE_NAME="${1:-dev}"

# Load env vars via cascade (shared + stage)
source "$SCRIPT_DIR/../common/load_env.sh" "$STAGE_NAME"

echo "Cleaning project: $COMPOSE_PROJECT_NAME..."
echo "This will remove containers, volumes, and networks."
read -p "Are you sure? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker compose -p "$COMPOSE_PROJECT_NAME" down --volumes --remove-orphans
    echo "✅ Cleaned."
else
    echo "Cancelled."
fi
