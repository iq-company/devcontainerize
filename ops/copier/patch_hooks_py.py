#!/usr/bin/env python3
"""Copier Task: Patch hooks.py to import ops_hooks.

This script adds a wildcard import at the end of hooks.py to include
all hooks defined in ops_hooks.py (ops_tests, ops_release_cleanup, etc.).

Usage: python3 patch_hooks_py.py <app_name>
"""

import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: patch_hooks_py.py <app_name>")
        sys.exit(1)

    app_name = sys.argv[1]
    hooks_path = Path(app_name) / "hooks.py"

    if not hooks_path.exists():
        print(f"[skip] {hooks_path} does not exist")
        return

    content = hooks_path.read_text()

    # The import line to add
    import_line = f"from {app_name}.ops_hooks import *"

    # Check if already imported
    if import_line in content:
        print(f"[ok] ops_hooks already imported in {hooks_path}")
        return

    # Also check for alternative import styles
    if f"import {app_name}.ops_hooks" in content:
        print(f"[ok] ops_hooks already imported in {hooks_path}")
        return

    # Check for legacy dist_hooks import and update it
    legacy_import = f"from {app_name}.dist_hooks import *"
    if legacy_import in content:
        content = content.replace(legacy_import, import_line)
        content = content.replace("# Import distribution hooks", "# Import operations hooks")
        hooks_path.write_text(content)
        print(f"[patch] Updated dist_hooks → ops_hooks in {hooks_path}")
        return

    # Add import at the end of the file
    if not content.endswith("\n"):
        content += "\n"

    content += f"\n# Import operations hooks (ops_tests, ops_release_cleanup, etc.)\n"
    content += f"{import_line}\n"

    hooks_path.write_text(content)
    print(f"[patch] Added ops_hooks import to {hooks_path}")


if __name__ == "__main__":
    main()
