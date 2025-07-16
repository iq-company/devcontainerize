#!/usr/bin/env bash

set -e  # Exit on errors

BENCH_DIR="/home/iqa/bench"
APPS_DIR="/home/iqa/bench/apps"

# Ensure all apps have .pth files in site-packages
echo "Setting up .pth files for all apps..."

ls -1 apps > /home/iqa/bench/sites/apps.txt;

# Find the site-packages directory dynamically
SITE_PACKAGES=$(find /home/{{ cookiecutter.image_user }}/bench/env/lib*/python*/site-packages -type d -name "site-packages" | head -n 1)

if [ -n "$SITE_PACKAGES" ]; then
    for app_dir in "$APPS_DIR"/*; do
        if [ -d "$app_dir" ]; then
            app_name=$(basename "$app_dir")
            pth_file="$SITE_PACKAGES/$app_name.pth"
            
            if [ ! -f "$pth_file" ]; then
                echo "Creating .pth file for $app_name"
                echo "$app_dir" > "$pth_file"
                echo "Created: $pth_file"
            else
                echo ".pth file for $app_name already exists"
            fi
        fi
    done
    echo "All .pth files have been set up successfully"
else
    echo "Error: Could not find site-packages directory"
    exit 1
fi
