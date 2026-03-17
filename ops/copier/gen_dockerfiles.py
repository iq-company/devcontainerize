#!/usr/bin/env python3
"""
Generate Dockerfiles from templates (copier task).

Called after copier copy/update to generate Dockerfiles via baker-cli.
The variant is passed by the copier task from the default_variant answer.

Usage (as copier task):
    python3 gen_dockerfiles.py <dst_path> [variant]
"""

import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("[skip] gen_dockerfiles.py: No destination path provided")
        return

    dst_path = Path(sys.argv[1])
    cli_variant = sys.argv[2] if len(sys.argv) > 2 else None

    settings_file = dst_path / "ops" / "build" / "build-settings.yml"

    if not settings_file.exists():
        print(f"[skip] gen_dockerfiles.py: Settings file not found: {settings_file}")
        return

    # Resolve variant: CLI arg > build-settings.yml > fallback
    variant = cli_variant or "debian"
    if not cli_variant:
        try:
            import yaml
            with open(settings_file) as f:
                settings = yaml.safe_load(f) or {}
            variant = settings.get("dockerfile_settings", {}).get("variant", "debian")
        except Exception:
            pass

    try:
        cmd = [
            sys.executable, "-m", "baker_cli", "gen-docker",
            "--settings", str(settings_file),
            "--variant", variant
        ]

        print(f"[task] Generating Dockerfiles (variant: {variant})...")
        result = subprocess.run(cmd, cwd=dst_path, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"[ok] Generated Dockerfiles in ops/build/docker/")
        else:
            if "No module named 'baker_cli'" in result.stderr:
                print("[skip] baker-cli not installed — run 'ops dockerfile create' after setup")
            elif "No Dockerfile templates found" in result.stderr:
                print("[skip] No templates found — run 'ops dockerfile create' after setup")
            else:
                print(f"[warn] gen_dockerfiles.py failed: {result.stderr.strip()}")

    except FileNotFoundError:
        print("[skip] baker-cli not available — run 'ops dockerfile create' after setup")


if __name__ == "__main__":
    main()
