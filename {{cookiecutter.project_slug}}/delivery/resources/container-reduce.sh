#!/usr/bin/bash

set -e
# get current python version
export PYTHON_VENV_VERSION=$(ls /home/iqa/bench/env/lib/ | grep -E '^python[0-9]+\.[0-9]+' | sort -V | tail -n 1)

# remove git dependencies from bench
sed -i 's/import git//' /home/iqa/bench/env/lib/$PYTHON_VENV_VERSION/site-packages/bench/utils/app.py
sed -i 's/import git//' /home/iqa/bench/env/lib/$PYTHON_VENV_VERSION/site-packages/bench/app.py

rm -rf apps/iq_core/.devcontainer \
	apps/iq_core/.github \
	apps/iq_core/.vscode \
	apps/iq_core/.gitignore \
	apps/iq_core/.git \
	apps/iq_core/delivery

# Clean up unnecessary files
cd /home/iqa/bench/apps/frappe &&
	rm -rf esbuild &&
	rm -rf node_modules/@babel &&
	rm -rf node_modules/@nodelib &&
	rm -rf node_modules/typescript &&
	rm -rf node_modules/html-janitor &&
	rm -rf node_modules/micromatch &&
	rm -rf node_modules/fast-glob &&
	rm -rf node_modules/loadjs &&
	# the reason for huge stdlib CVEs in golang
	rm -rf node_modules/esbuild-linux-64 &&
	rm -rf node_modules/esbuild* &&
	# reduce unneeded files in node_modules by yarn
	yarn autoclean --init && yarn autoclean --force &&
	# reduce (yet unneeded) cve pips
	pip uninstall -y pip &&
	rm -rf /home/iqa/bench/env/lib/python3*/site-packages/h11/tests/ &&
	rm -rf /home/iqa/bench/env/lib/python3*/site-packages/parso*

# DONT do this, if LOCAL_DEV_ENV=true (this means in this container, the local git will be mounted) !
if [ "$LOCAL_DEV_ENV" != "true" ]; then
	/usr/bin/find /home/iqa/bench/apps -type d \( -name ".cache" -o -name ".config" -o -name ".yarn" -o -name ".git" \) -exec rm -rf {} +
	\ find /home/iqa/bench/apps -mindepth 1 -path "*/.git" | xargs rm -fr
	/usr/bin/find /home/iqa/bench/apps -mindepth 1 -path "*/.github" | xargs rm -fr
fi
