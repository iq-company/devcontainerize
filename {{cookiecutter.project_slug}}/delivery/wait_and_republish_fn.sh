#!/bin/bash

function ensure_aws_ecr_login() {
    # Load script file directory into variable
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Check if .env file exists in the script's directory. If not, exit with instructions to create it.
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        echo "Die .env-Datei wurde nicht gefunden."
        echo "Bitte kopieren Sie die .env.example zu .env und füllen Sie die entsprechenden Werte aus."
		echo "cp $SCRIPT_DIR/.env.example $SCRIPT_DIR/.env && vim $SCRIPT_DIR/.env"
        exit 1
    fi

    # Load .env file
    source "$SCRIPT_DIR/.env"

    # Check if there is an active session
    if aws ecr describe-repositories >/dev/null 2>&1; then
        # Aktive Session vorhanden
        echo "Active AWS ECR Session available."
        return 0
    else
        # No active session in ECR
        if [ -n "$AWS_SESSION_TOKEN" ]; then
            # AWS_SESSION_TOKEN ist gesetzt
            if aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin "$AWS_ECR_ACCOUNT"; then
                echo "AWS ECR Login successful."
                return 0
            else
                # Login failed, delete AWS_SESSION_TOKEN ENV
                unset AWS_SESSION_TOKEN
                echo "AWS ECR Login failed."
            fi
        fi

        # Start browser to login
        open "$AWS_ACCOUNT_WEB"

        # Anweisungen ausgeben
        echo "Please continue with the following steps:"
		echo "1. Login at the AWS Console in the opened browser (url: $AWS_ACCOUNT_WEB)."
        echo "2. Expand 'Container Landscape'."
        echo "3. Click on the Link 'Access Keys'."
        echo "4. Copy the variables for 'Option 1'."
        echo "5. Paste in the terminal, press Enter and re-run this script command."

        exit 1
    fi
}

function wait_and_republish_img() {
    PARAM=$1
    IMAGE_TARGET=${2:-iq-core}

    if [ -z "$PARAM" ]; then
        echo "Bitte geben Sie einen Registrytyp oder 'local:<imagename>' als Argument an."
        echo "Beispielaufrufe:"
        echo "  $0 gh"
        echo "  $0 local:iqf"
        echo "  $0 local:iqf:v1.2.3"
        echo "  $0 local:iqf:latest:v15.13.2 mein-custom-image"
        exit 1
    fi

    # Versionsnummer aus container-version holen
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    VERS=$(cat "$SCRIPT_DIR/container-version")

    if [[ "$PARAM" == local:* ]]; then
        # Extract tag_name from local:tag_name
        IMAGE_WITH_TAG=${PARAM#local:}  # Remove leading "local:"

        IFS=':' read -r LOCAL_IMAGE_NAME LOCAL_SOURCE_TAG LOCAL_TARGET_TAG <<< "$IMAGE_WITH_TAG"

        # Extract (fallback) values
        LOCAL_SOURCE_TAG=${LOCAL_SOURCE_TAG:-latest}
        LOCAL_TARGET_TAG=${LOCAL_TARGET_TAG:-$LOCAL_SOURCE_TAG}

        SRC_IMG="$LOCAL_IMAGE_NAME:$LOCAL_SOURCE_TAG"
        VERS=${LOCAL_TARGET_TAG:-$VERS}

        echo "Using local Image: $SRC_IMG"
        docker pull "$SRC_IMG" 2>/dev/null || echo "Using local image without pulling"
    else
        # Paketregistrypfad aus Umgebungsvariable holen
        REGISTRY_PATH_VAR="PACKAGE_REGISTRY_${PARAM}"
        REGISTRY_PATH="${!REGISTRY_PATH_VAR}"

        if [ -z "$REGISTRY_PATH" ]; then
            echo "Umgebungsvariable $REGISTRY_PATH_VAR ist nicht gesetzt."
            return 1
        fi

        SRC_IMG="${REGISTRY_PATH}:${VERS}"
        echo "Checking for image: $SRC_IMG"

        # Auf Verfügbarkeit des Tags in der Registry warten
        while ! docker manifest inspect "$SRC_IMG" &>/dev/null; do
            echo "Waiting for $SRC_IMG to become available..."
            sleep 15
        done

        echo "Image $SRC_IMG is now available, pulling..."
        docker pull "$SRC_IMG"
    fi

    DEST_IMG="$AWS_ECR_ACCOUNT/$IMAGE_TARGET:$VERS"
    echo "Dest Image: $DEST_IMG"

    # Re-tag to the aws image
    docker tag "$SRC_IMG" "$DEST_IMG"

    # Push it
    if docker push "$DEST_IMG"; then
        echo "Pushed: $DEST_IMG"
    fi
}

ensure_aws_ecr_login

# call function with script arguments
wait_and_republish_img "$1" "$2"

