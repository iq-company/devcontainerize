#!/usr/bin/env python3
"""Copier Task: Add baker-cli to pyproject.toml dev dependencies.

This script modifies an existing pyproject.toml to add baker-cli
as a development dependency without overwriting the entire file.

Only runs when feature_image_creation is enabled (which requires baker-cli
for building Docker images).

Usage: python3 patch_pyproject_toml.py <project_root> <feature_image_creation>
"""

import subprocess
import sys
import re
from pathlib import Path


def run_pip_install(project_root: Path) -> bool:
    """Run pip install -e '.[dev]' and return success status."""
    print("\n" + "=" * 60)
    print("Installing dev dependencies (including baker-cli)...")
    print("=" * 60)

    try:
        result = subprocess.run(
            ["pip", "install", "-e", ".[dev]"],
            cwd=project_root,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("✓ Successfully installed dev dependencies")
            print("\nYou can now use baker-cli:")
            print("  baker plan              # Show build plan")
            print("  baker build --targets dev  # Build dev image")
            return True
        else:
            print(f"✗ pip install failed (exit code {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr[:500]}")
            print("\nPlease run manually:")
            print(f"  cd {project_root}")
            print("  pip install -e '.[dev]'")
            return False

    except FileNotFoundError:
        print("✗ pip not found in PATH")
        print("\nPlease run manually:")
        print(f"  cd {project_root}")
        print("  pip install -e '.[dev]'")
        return False


def patch_pyproject(project_root: Path) -> bool:
    """Add baker-cli to pyproject.toml. Returns True if patched or already present."""
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"[skip] pyproject.toml not found at {pyproject_path}")
        return False

    content = pyproject_path.read_text(encoding="utf-8")

    # Check if baker-cli is already present
    if "baker-cli" in content:
        print("[ok] baker-cli already in pyproject.toml")
        return True

    # Strategy 1: Look for existing dev dependencies in [project.optional-dependencies]
    dev_deps_pattern = r'(\[project\.optional-dependencies\].*?dev\s*=\s*\[)([^\]]*?)(\])'
    match = re.search(dev_deps_pattern, content, re.DOTALL)

    if match:
        before = match.group(1)
        existing = match.group(2).strip()
        after = match.group(3)

        if existing:
            new_deps = f'{existing},\n    "baker-cli",'
        else:
            new_deps = '\n    "baker-cli",\n'

        new_content = content[:match.start()] + before + new_deps + after + content[match.end():]
        pyproject_path.write_text(new_content, encoding="utf-8")
        print("[patch] Added baker-cli to [project.optional-dependencies] dev")
        return True

    # Strategy 2: Look for [tool.uv.dev-dependencies]
    uv_dev_pattern = r'(\[tool\.uv\.dev-dependencies\].*?)((?=\n\[)|\Z)'
    match = re.search(uv_dev_pattern, content, re.DOTALL)

    if match:
        section = match.group(1)
        if "baker-cli" not in section:
            new_section = section.rstrip() + '\nbaker-cli = ">=0.1.0"\n'
            new_content = content[:match.start()] + new_section + content[match.end():]
            pyproject_path.write_text(new_content, encoding="utf-8")
            print("[patch] Added baker-cli to [tool.uv.dev-dependencies]")
            return True

    # Strategy 3: Create new optional-dependencies section
    if "[project.optional-dependencies]" not in content:
        # Find end of [project] section
        project_start = content.find("[project]")
        if project_start != -1:
            project_section_end = content.find("\n[", project_start + 1)
            if project_section_end == -1:
                project_section_end = len(content)

            new_section = """
[project.optional-dependencies]
dev = [
    "baker-cli",
]
"""
            new_content = content[:project_section_end] + new_section + content[project_section_end:]
            pyproject_path.write_text(new_content, encoding="utf-8")
            print("[patch] Created [project.optional-dependencies] with baker-cli")
            return True

    print("[skip] Could not find suitable location to add baker-cli")
    return False


def main():
    if len(sys.argv) < 3:
        print("Usage: patch_pyproject_toml.py <project_root> <feature_image_creation>")
        sys.exit(1)

    project_root = Path(sys.argv[1]).resolve()
    feature_image_creation = sys.argv[2].lower() in ("true", "1", "yes")

    # Only patch if image_creation feature is enabled
    if not feature_image_creation:
        print("[skip] feature_image_creation is disabled, baker-cli not needed")
        return

    print("\n" + "=" * 60)
    print("Setting up baker-cli for Docker image builds")
    print("=" * 60 + "\n")

    # Step 1: Patch pyproject.toml
    patched = patch_pyproject(project_root)

    if not patched:
        print("\n⚠ Could not add baker-cli to pyproject.toml")
        print("Please add manually to your dev dependencies:")
        print('  [project.optional-dependencies]')
        print('  dev = ["baker-cli"]')
        return

    # Step 2: Install dev dependencies
    run_pip_install(project_root)


if __name__ == "__main__":
    main()
