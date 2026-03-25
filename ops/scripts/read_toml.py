#!/usr/bin/env python3
"""
Read values from pyproject.toml [tool.ops.overrides] for use in shell scripts.

Usage from bash:
    # Read a list (one item per line):
    PACKAGES=$(python3 read_toml.py list tool.ops.overrides.frappe-pip-removals.packages)

    # Read a key-value table (tab-separated):
    python3 read_toml.py table tool.ops.overrides.frappe-pip-upgrades
    # Output: markdown2\t~=2.5.0
    #         pypdf\t~=6.7

    # Read a single value:
    python3 read_toml.py value tool.ops.frappe.branch
    # Output: version-15

The script auto-discovers pyproject.toml by walking up from the script
location (ops/scripts/) to the app root.
"""

import sys
import tomllib
from pathlib import Path


def _find_pyproject() -> Path:
    """Find pyproject.toml relative to this script's location."""
    script_dir = Path(__file__).resolve().parent
    # ops/scripts/ -> app root is two levels up
    candidate = script_dir.parents[1] / "pyproject.toml"
    if candidate.exists():
        return candidate

    # Also accept an explicit path via env or argument
    for arg in sys.argv:
        p = Path(arg)
        if p.name == "pyproject.toml" and p.exists():
            return p

    # Walk up until we find it
    for parent in script_dir.parents:
        p = parent / "pyproject.toml"
        if p.exists():
            return p

    print("ERROR: pyproject.toml not found", file=sys.stderr)
    sys.exit(1)


def _resolve(data: dict, dotpath: str):
    """Resolve a dot-separated key path like 'tool.ops.overrides.x'."""
    keys = dotpath.split(".")
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return None
        if data is None:
            return None
    return data


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <list|table|value> <dotpath>", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]
    dotpath = sys.argv[2]

    pyproject = _find_pyproject()
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)

    result = _resolve(data, dotpath)

    if result is None:
        sys.exit(0)

    if mode == "list":
        if isinstance(result, list):
            for item in result:
                print(item)
        else:
            print(result)

    elif mode == "table":
        if isinstance(result, dict):
            for key, val in result.items():
                if key == "packages":
                    continue
                print(f"{key}\t{val}")
        else:
            print(result)

    elif mode == "value":
        print(result)

    else:
        print(f"Unknown mode: {mode}  (use: list, table, value)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
