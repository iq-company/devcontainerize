#!/usr/bin/bash

set -e

CWD="$(pwd)"

if [ -d "apps" ] && [ -d "sites" ]; then
    APP_TARGET_DIR="${CWD}/apps/iq_core"
	ACTIVATED_PACKAGES_FILE="${CWD}/apps/iq_core/activated_packages"
elif [ -d "bench" ]; then
	APP_TARGET_DIR="${CWD}/bench/apps/iq_core"
	ACTIVATED_PACKAGES_FILE="${CWD}/bench/apps/iq_core/activated_packages"
else
    # Case 3: Invalid CWD, exit with error
    echo "Error: Invalid current working directory."
    exit 1
fi

# remove frappe billing package, as this has own huge npms etc. (and isnt needed at all)
rm -rf "$APP_TARGET_DIR/../frappe/billing"

# Pfad zur pyproject.toml-Datei
PYPROJECT_FILE="$APP_TARGET_DIR/pyproject.toml"
> "$ACTIVATED_PACKAGES_FILE"

# Überprüfen, ob die Datei existiert
if [ ! -f "$PYPROJECT_FILE" ]; then
    echo "The file $PYPROJECT_FILE couldnt be found."
    exit 1
fi

# Maps the environment variables to the corresponding packages
declare -A package_map=(
    [ENABLE_TRANSFORMERS]="transformers sentence-transformers"
    [ENABLE_PANDAS]="pandas"
    [ENABLE_OCR]="rapidocr-onnxruntime"
    [ENABLE_DOC_READER]="pypdf docx2txt unstructured fsspec python-pptx"
    [ENABLE_NLP]="spacy"
    [ENABLE_CHROMADB_CLIENT]="chromadb opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc opentelemetry-exporter-otlp-proto-grpc",
    [ENABLE_LANGCHAIN]="grpcio langchain langchain-community"
    [ENABLE_APIFY_CLIENT]="apify_client"
    [ENABLE_LANGUAGE_DETECTION]="lingua-language-detector"
)

# dependencies that need to be set in the environment (separate multiple dependencies with space)
declare -A env_dependencies=(
    [ENABLE_OCR]="ENABLE_LANGCHAIN"
    [ENABLE_DOC_READER]="ENABLE_LANGCHAIN"
)

is_env_active() {
    local env_var="$1"
    local value=$(printenv "$env_var")
    if [ "$value" == "true" ]; then
        return 0  # True
    else
        return 1  # False
    fi
}

is_env_needed() {
    local env_var="$1"

    # Wenn das ENV bereits verarbeitet wurde, direkt zurückkehren
    if [ "${processed_envs[$env_var]}" == "true" ]; then
        return 0
	else
        return 1
    fi

    # Überprüfen, ob das ENV direkt aktiviert ist
    if is_env_active "$env_var"; then
        # Markiere das ENV als verarbeitet und aktiv
        processed_envs[$env_var]="true"
        # Schreibe die zugehörigen Pakete in die activated_packages-Datei
        IFS=' ' read -r -a pkgs <<< "${package_map[$env_var]}"
        for pkg in "${pkgs[@]}"; do
            echo "$pkg" >> "$ACTIVATED_PACKAGES_FILE"
        done
        return 0
    fi

    # Überprüfen, ob andere ENVs von diesem ENV abhängig sind und aktiviert sind
    for dependent_env in "${!env_dependencies[@]}"; do
        dependencies="${env_dependencies[$dependent_env]}"
        # Überprüfen, ob das aktuelle ENV in den Abhängigkeiten des dependent_env enthalten ist
        if [[ $dependencies == *"$env_var"* ]]; then
            if is_env_needed "$dependent_env"; then
                # Markiere das ENV als verarbeitet und aktiv
                processed_envs[$env_var]="true"
                # Schreibe die zugehörigen Pakete in die activated_packages-Datei
                IFS=' ' read -r -a pkgs <<< "${package_map[$env_var]}"
                for pkg in "${pkgs[@]}"; do
                    echo "$pkg" >> "$ACTIVATED_PACKAGES_FILE"
                done
                return 0
            fi
        fi
    done

    # Markiere das ENV als verarbeitet und nicht aktiv
    processed_envs[$env_var]="false"
    return 1
}

# Removes the specified packages from the [project] section
remove_packages() {
    local packages=("$@")
    for pkg in "${packages[@]}"; do
        sed -i "/^[[:space:]]*\"${pkg//\./\\.}\([^\"]*\)\"[[:space:]]*,\{0,1\}[[:space:]]*$/d" "$PYPROJECT_FILE"
    done
}

for env_var in "${!package_map[@]}"; do
    if is_env_needed "$env_var"; then
        echo "Keep modules for $env_var"
    else
        IFS=' ' read -r -a pkgs <<< "${package_map[$env_var]}"
        remove_packages "${pkgs[@]}"
        echo "Drop pip modules for $env_var: ${pkgs[*]}"
    fi
done

