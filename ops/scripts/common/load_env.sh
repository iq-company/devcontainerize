#!/bin/bash
# Load shared .env and stage-specific .env.STAGE
# Usage: source load_env.sh [stage]
# Default stage: dev

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$(cd "$SCRIPT_DIR/../../compose" && pwd)"
STAGE="${1:-dev}"

# Load shared defaults first
[ -f "$ENV_DIR/.env" ] && source "$ENV_DIR/.env"

# Load stage-specific overrides
[ -f "$ENV_DIR/.env.$STAGE" ] && source "$ENV_DIR/.env.$STAGE"
