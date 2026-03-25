#!/usr/bin/env python3
"""Copier Task: Patch pyproject.toml for devcontainerize features.

This script modifies an existing pyproject.toml to:
  1. Add baker-cli as a dev dependency (when feature_image_creation is enabled)
  2. Add [tool.ops.frappe] and [tool.ops.overrides] sections for centralized
     dependency and build configuration (used by ops deps CLI and build scripts)

Usage: python3 patch_pyproject_toml.py <project_root> <feature_image_creation> [frappe_branch]
"""

import subprocess
import sys
import re
from pathlib import Path


OPS_SECTIONS_TEMPLATE = """\

# =============================================================================
# ops CLI — dependency & build configuration
# =============================================================================
# Managed by:  ops deps fix | free | update-stable | update-experimental
# Read by:     build scripts via  python3 read_toml.py

[tool.ops.frappe]
branch = "{frappe_branch}"
version = ""                   # tag (e.g. "15.102.1") or commit SHA — empty = branch HEAD

# -----------------------------------------------------------------------------
# Build-script overrides (consumed by frappe-patches.sh, cleaners, etc.)
# Centralizes all dependency decisions so they are reviewable in one file.
# -----------------------------------------------------------------------------

[tool.ops.overrides.frappe-pip-upgrades]
# Version upgrades applied to frappe's pyproject.toml (CVE fixes)
# Example:
markdown2 = "~=2.5.0"         # CVE: XSS/ReDoS in 2.4.x
pypdf = "~=6.7"               # CVE in 3.x
PyJWT = "~=2.12.0"            # CVE in <=2.8.0

[tool.ops.overrides.frappe-pip-removals]
# Packages removed from frappe's pyproject.toml (unused modules)
# packages = [
#     "PyMySQL", "PyQRCode", "ldap3", "terminaltables",
#     "sentry-sdk", "vobject", "pdfkit",
# ]
packages = []

[tool.ops.overrides.frappe-npm-upgrades]
# Version upgrades in frappe's package.json
"socket.io" = "^4.8.3"           # CVE: DoS via ws in 4.7.x
"socket.io-client" = "^4.8.1"
superagent = "^10.0.0"           # CVE: arbitrary file upload in 8.x

[tool.ops.overrides.npm-resolutions]
# CVE fixes applied as yarn/npm resolutions to all apps' package.json
"@adobe/css-tools" = "4.3.3"
"loader-utils" = "^3.2.0"
postcss = "8.4.47"
braces = "3.0.3"
ws = "8.18.3"
qs = "6.14.2"
"markdown-it" = "14.1.1"
minimatch = "3.1.5"

[tool.ops.overrides.release-venv-removals]
# Packages uninstalled from the release image venv (dev-only tools)
# packages = ["jedi", "parso", "IPython"]
packages = []

[tool.ops.overrides.dev-venv-removals]
# Packages uninstalled from the dev image venv
# packages = ["jedi", "parso"]
packages = []
"""


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


def patch_ops_sections(project_root: Path, frappe_branch: str) -> bool:
    """Add [tool.ops.frappe] and [tool.ops.overrides] sections if not present."""
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        return False

    content = pyproject_path.read_text(encoding="utf-8")

    if "[tool.ops.frappe]" in content:
        print("[ok] [tool.ops.frappe] already in pyproject.toml")
        return True

    sections = OPS_SECTIONS_TEMPLATE.format(frappe_branch=frappe_branch)
    content = content.rstrip() + "\n" + sections
    pyproject_path.write_text(content, encoding="utf-8")
    print(f"[patch] Added [tool.ops.frappe] and [tool.ops.overrides] sections (branch: {frappe_branch})")
    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: patch_pyproject_toml.py <project_root> <feature_image_creation> [frappe_branch]")
        sys.exit(1)

    project_root = Path(sys.argv[1]).resolve()
    feature_image_creation = sys.argv[2].lower() in ("true", "1", "yes")
    frappe_branch = sys.argv[3] if len(sys.argv) > 3 else "version-15"

    if not feature_image_creation:
        print("[skip] feature_image_creation is disabled, skipping pyproject patches")
        return

    print("\n" + "=" * 60)
    print("Setting up pyproject.toml for Docker image builds")
    print("=" * 60 + "\n")

    # Step 1: Add [tool.ops.frappe] + [tool.ops.overrides] sections
    patch_ops_sections(project_root, frappe_branch)

    # Step 2: Add baker-cli to dev dependencies
    patched = patch_pyproject(project_root)

    if not patched:
        print("\n⚠ Could not add baker-cli to pyproject.toml")
        print("Please add manually to your dev dependencies:")
        print('  [project.optional-dependencies]')
        print('  dev = ["baker-cli"]')
        return

    # Step 3: Install dev dependencies
    run_pip_install(project_root)


if __name__ == "__main__":
    main()
