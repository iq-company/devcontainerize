#!/usr/bin/env python3
"""
Copier task to initialize the dev stage after template copy/update.

This script:
1. Creates the .env file for the dev stage (if it doesn't exist)
2. Prints instructions for building the dev image
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 4:
        print("Usage: init_dev_stage.py <dst_path> <image_prefix> <default_dbms>")
        sys.exit(1)

    dst_path = Path(sys.argv[1])
    image_prefix = sys.argv[2]
    default_dbms = sys.argv[3]

    compose_dir = dst_path / "ops" / "compose"
    env_file = compose_dir / ".env"
    init_script = dst_path / "ops" / "scripts" / "devcontainer" / "init_env_files"

    # Check if .env already exists
    if env_file.exists():
        print(f"[ok] Environment file already exists: {env_file}")
        return

    # Check if init script exists
    if not init_script.exists():
        print(f"[skip] Init script not found: {init_script}")
        return

    # Create the .env file
    print("\n" + "=" * 60)
    print("Initializing dev stage environment")
    print("=" * 60 + "\n")

    result = subprocess.run(
        ["bash", str(init_script), default_dbms],
        cwd=dst_path,
        env={**os.environ, "ENV_FILE_SUFFIX": ""}  # Empty suffix for dev stage
    )

    if result.returncode != 0:
        print(f"[error] Failed to create .env file")
        return

    # Print next steps
    image_name = f"{image_prefix}-dev"

    print("\n" + "=" * 60)
    print("🎉 Template setup complete!")
    print("=" * 60)
    print(f"""
Next steps to start developing:

1. Build the dev image (required before first start):

   bench ops stage build dev

   This creates the Docker image '{image_name}' with Frappe
   and your app pre-installed.

2. Start the devcontainer:

   - Open this folder in VS Code
   - Click "Reopen in Container" when prompted (if not prompted, use F1 and begin typing "Dev Container: Reopen Folder in Container" and choose it)

3. (Optional) Configure a registry for team sharing:

   Edit ops/build/stages.yml and set:
     image: ghcr.io/your-org/your-repo/{image_name}:latest

   Then team members can pull instead of building.
""")


if __name__ == "__main__":
    main()
