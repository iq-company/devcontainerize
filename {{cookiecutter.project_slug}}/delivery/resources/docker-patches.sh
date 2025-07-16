#!/usr/bin/bash

set -e

# These patches are called with root user in directory /home/${IMAGE_USER}/bench
# Patches in container libraries are applied.

# get current python version
export PYTHON_VENV_VERSION=$(ls /home/${IMAGE_USER}/bench/env/lib/ | grep -E '^python[0-9]+\.[0-9]+' | sort -V | tail -n 1)

# setup logstash monkey_patches
INSERT_LINE="import iq_core.monkey_patches.inject_json_logstash"

sed -i "/import sys/a $INSERT_LINE" "/home/${IMAGE_USER}/bench/env/lib/$PYTHON_VENV_VERSION/site-packages/bench/cli.py"
sed -i "/import sys/a $INSERT_LINE" "apps/frappe/frappe/commands/scheduler.py"

# Install required models (like nlp models)
#
# Reads given environment activation and content variable and returns the content as iterable list
#
# e.g. ENABLE_NLP=true and ENABLE_NLP_MODELS="en_core_web_sm de_core_news_sm"
# will return "en_core_web_sm de_core_news_sm" (but only if ENABLE_NLP is true)
#
get_models() {
	local env_var="$1"
	local models_suffix="$2"

	# Checks if activation var is set to true
	local env_value=$(printenv "$env_var")
	if [ "$env_value" != "true" ]; then
		return 0
	fi

	# Build concatenated content variable name
	local models_env_var="${env_var}_${models_suffix}"

	local models_value=$(printenv "$models_env_var")
	if [ -z "$models_value" ]; then
		return 0
	fi

	# Return the value
	echo "$models_value"
}

nlp_models=$(get_models "ENABLE_NLP" "MODELS")
if [ -n "$nlp_models" ]; then
	# first of all install spacy (as this is not part of pyproject.toml)
	pip install spacy

	IFS=' ' read -r -a nlp_models_array <<<"$nlp_models"
	for model in "${nlp_models_array[@]}"; do
		echo "Installs SpaCy NLP-Modell: $model"
		python -m spacy download "$model"
	done
fi

tf_models=$(get_models "ENABLE_TRANSFORMERS" "MODELS")
if [ -n "$tf_models" ]; then
	IFS=' ' read -r -a tf_models_array <<<"$tf_models"
	for model in "${tf_models_array[@]}"; do
		echo "Installs Huggingface Transformers-Modell: $model"
		python -c "from transformers import $model; print($model)"
	done
fi

# Final changes as check if previous commands didnt fail so far:
# app name manipulation
sed -i "s/IQ Flow/${IQ_BRAND_NAME:-IQ Flow}/g" /home/${IMAGE_USER}/bench/apps/iq_core/iq_core/hooks.py

# also change brand in workspace json
sed -i "s/IQ Flow/${IQ_BRAND_NAME:-IQ Flow}/g" apps/iq_core/iq_core/iq_core/workspace/iq_flow/iq_flow.json

# final splash screen manipulation
sed -i "s/__(\"Starting Frappe ...\")/__(\"Starting ${IQ_BRAND_NAME:-IQ Flow} ...\")/" /home/${IMAGE_USER}/bench/apps/frappe/frappe/desk/page/setup_wizard/setup_wizard.js
