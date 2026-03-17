#!/bin/bash
# =============================================================================
# DevContainer Pre-flight Check
# =============================================================================
# Called BEFORE init_env_files in devcontainer.json initializeCommand.
# Produces NO output on success. On failure, shows a clear error and exits
# before Docker Compose starts — preventing the wall of cryptic errors.
# =============================================================================

fail() {
	local heading="$1"; shift

	# Write a Markdown file into the workspace — VSCode renders it nicely
	SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
	ERR_FILE="$(cd "$SCRIPT_DIR/../.." && pwd)/DEVCONTAINER_ERROR.md"
	{
		echo "# DevContainer cannot start"
		echo ""
		echo "## $heading"
		echo ""
		for line in "$@"; do echo "- $line"; done
		echo ""
		echo "---"
		echo "*Fix the issue above, then run \`Dev Containers: Reopen in Container\` again.*"
		echo "*This file is deleted automatically on successful start.*"
	} > "$ERR_FILE"

	# Open the file as a tab in VSCode (visible, impossible to miss)
	code "$ERR_FILE" 2>/dev/null || true

	exit 1
}

# 1. Docker installed?
command -v docker &>/dev/null || fail \
	"Docker is not installed or not in PATH." \
	"Install Docker: https://docs.docker.com/get-docker/"

# 2. Docker daemon running?
docker info &>/dev/null || fail \
	"Docker daemon is not running or you lack permission." \
	"Start Docker Desktop / the Docker service, or:" \
	"  sudo usermod -aG docker \$USER"

# 3. Dev image exists? (source existing env if available for image name)
SCRIPT_DIR="${SCRIPT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
COMPOSE_ENV="$(cd "$SCRIPT_DIR/../../compose" 2>/dev/null && pwd)/.env"
[ -f "$COMPOSE_ENV" ] && source "$COMPOSE_ENV"
IMG="${IQ_IMAGE:-iq-dev}:${IQ_IMAGE_TAG:-latest}"

docker image inspect "$IMG" &>/dev/null || fail \
	"Docker image '${IMG}' not found." \
	"The DevContainer cannot start without this image." \
	"Build it first, e.g.:  bench ops build dev"

# All checks passed — clean up any previous error file
OPS_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
rm -f "$OPS_DIR/DEVCONTAINER_ERROR.md"
