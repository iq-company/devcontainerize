#!/usr/bin/env bash
set -ex

mkdir -p /iq_sites/extensions
state_file=/iq_sites/extensions/ocr_current

if [ -f "$state_file" ]; then
  cd /iq_sites/extensions
  for line in $(cat "$state_file"); do
    grep "$line" *_current --exclude "$state_file" || rm -rfv "$line"
  done
fi

if [ -z "${IQ_PIP_EXTENSION_DIR}" ]; then
  echo "IQ_PIP_EXTENSION_DIR not set. Aborting."
  exit 1
fi

rsync -av "${IQ_PIP_EXTENSION_DIR}" "/iq_sites/extensions"
ls -1a /iq_sites/extensions/pip_packages > "$state_file"

