#!/usr/bin/env python3
"""
Generate Dockerfiles from templates after copier copy/update.

This script is called as a copier task to generate the initial Dockerfiles
from the docker-templates/*.j2 files using baker-cli.

Usage (as copier task):
    python3 gen_dockerfiles.py <dst_path> [--variant debian]
"""

import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("[skip] gen_dockerfiles.py: No destination path provided")
        return

    dst_path = Path(sys.argv[1])
    variant = sys.argv[2] if len(sys.argv) > 2 else "debian"

    settings_file = dst_path / "ops" / "build" / "build-settings.yml"
    docker_dir = dst_path / "ops" / "build" / "docker"

    # Check if settings file exists
    if not settings_file.exists():
        print(f"[skip] gen_dockerfiles.py: Settings file not found: {settings_file}")
        return

    # Check if Dockerfiles already exist (skip regeneration on update)
    existing_dockerfiles = list(docker_dir.glob("Dockerfile.*"))
    if existing_dockerfiles and "--force" not in sys.argv:
        print(f"[ok] Dockerfiles already exist in {docker_dir.name}/")
        print("     Run 'bench ops dockerfile update' to regenerate")
        return

    # Try to run baker gen-docker
    try:
        cmd = [
            sys.executable, "-m", "baker_cli", "gen-docker",
            "--settings", str(settings_file),
            "--variant", variant
        ]

        print(f"[task] Generating Dockerfiles (variant: {variant})...")
        result = subprocess.run(cmd, cwd=dst_path, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"[ok] Generated Dockerfiles in {docker_dir.name}/")
        else:
            # baker-cli might not be installed yet
            if "No module named 'baker_cli'" in result.stderr:
                print("[skip] baker-cli not installed yet")
                print("       Run 'bench ops dockerfile create' after installation")
            elif "No Dockerfile templates found" in result.stderr:
                print("[skip] No Dockerfile templates found yet")
                print("       Run 'bench ops dockerfile create' after copier update")
            else:
                print(f"[warn] gen_dockerfiles.py failed: {result.stderr.strip()}")

    except FileNotFoundError:
        print("[skip] Python/baker-cli not available")
        print("       Run 'bench ops dockerfile create' after setup")


if __name__ == "__main__":
    main()
