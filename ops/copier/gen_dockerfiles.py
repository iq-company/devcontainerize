#!/usr/bin/env python3
"""
Generate Dockerfiles from templates after copier copy.

Only runs in a real project directory (.git present). During copier update,
tasks also execute in temp directories for old-vs-new comparison — the script
skips those so copier's 3-way merge never touches generated Dockerfiles.

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

    # Skip in copier's temp comparison directories (no .git = not a real project).
    # This ensures copier's old-vs-new diff never includes generated Dockerfiles,
    # so the user's existing files are left untouched during updates.
    if not (dst_path / ".git").exists():
        return

    settings_file = dst_path / "ops" / "build" / "build-settings.yml"
    docker_dir = dst_path / "ops" / "build" / "docker"

    if not settings_file.exists():
        print(f"[skip] gen_dockerfiles.py: Settings file not found: {settings_file}")
        return

    # Skip if Dockerfiles already exist (update, not initial copy)
    existing_dockerfiles = list(docker_dir.glob("Dockerfile.*"))
    if existing_dockerfiles and "--force" not in sys.argv:
        print(f"[ok] Dockerfiles already exist in {docker_dir.name}/")
        print("     Run 'ops dockerfile update' to regenerate")
        return

    # Resolve variant: CLI arg > build-settings.yml > fallback
    cli_variant = sys.argv[2] if len(sys.argv) > 2 else None
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
            print(f"[ok] Generated Dockerfiles in {docker_dir.name}/")
        else:
            if "No module named 'baker_cli'" in result.stderr:
                print("[skip] baker-cli not installed — run 'ops dockerfile create' after setup")
            elif "No Dockerfile templates found" in result.stderr:
                print("[skip] No templates found — run 'ops dockerfile create' after copier update")
            else:
                print(f"[warn] gen_dockerfiles.py failed: {result.stderr.strip()}")

    except FileNotFoundError:
        print("[skip] Python/baker-cli not available — run 'ops dockerfile create' after setup")


if __name__ == "__main__":
    main()
