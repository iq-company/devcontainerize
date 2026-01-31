#!/usr/bin/env python3
"""Copier Task: Move .copier-answers.yml to ops/build/

This script moves the .copier-answers.yml file from the project root
to ops/build/.copier-answers.yml after copier copy/update.

This allows keeping the root directory clean while still supporting
copier updates via `bench ops template update`.

Usage: python3 move_copier_answers.py <project_root>
"""

import shutil
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: move_copier_answers.py <project_root>")
        sys.exit(1)

    project_root = Path(sys.argv[1]).resolve()

    source = project_root / ".copier-answers.yml"
    target_dir = project_root / "ops" / "build"
    target = target_dir / ".copier-answers.yml"

    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    if source.exists():
        # Move the file
        shutil.move(str(source), str(target))
        print(f"✓ Moved .copier-answers.yml to {target.relative_to(project_root)}")
    elif target.exists():
        print(f"[ok] .copier-answers.yml already at {target.relative_to(project_root)}")
    else:
        print("[skip] No .copier-answers.yml found")


if __name__ == "__main__":
    main()
