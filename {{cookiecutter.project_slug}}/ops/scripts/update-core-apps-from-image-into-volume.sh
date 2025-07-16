#!/bin/bash
set -e

# Load vars
source ops/compose/.env

VOLUME_NAME="${COMPOSE_PROJECT_NAME}_apps"
IMAGE_TAG="${IQ_IMAGE}:${IQ_IMAGE_TAG}"
TMP_CONTAINER="core-update-temp"

echo "Checking if volume exists..."
if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
	echo "Volume $VOLUME_NAME not found! Skipping"
	exit 1
fi

echo "Creating temporary container from image $IMAGE_TAG..."
docker run --rm --name "$TMP_CONTAINER" \
	-v "$VOLUME_NAME":/mnt/apps \
	"$IMAGE_TAG" \
	bash -c '
	  set -e
	  TARGET="/mnt/apps/frappe"
	  SOURCE="/home/{{ cookiecutter.image_user }}/bench/apps/frappe"

	  echo "Removing old frappe in volume (if exists)..."
	  rm -rf "$TARGET"

	  echo "Copying new frappe from image..."
	  cp -a "$SOURCE" "$TARGET"
	'

echo "✅ Updated Core App from Image in volume $VOLUME_NAME."
