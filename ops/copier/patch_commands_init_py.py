#!/usr/bin/env python3
"""Copier Task: Patch commands/__init__.py to import all *_commands modules.

This script modifies an existing __init__.py to add imports for all
*_commands.py files found in the template's commands directory.

It dynamically discovers command modules, so new *_commands.py files
are automatically included without modifying this script.

Usage: python3 patch_commands_init_py.py <app_name> [template_commands_dir]
"""

import sys
from pathlib import Path


def discover_command_modules(template_commands_dir: Path) -> list[tuple[str, str]]:
    """Discover all *_commands.py.jinja files in the template directory.

    Returns list of tuples: (module_name, import_line)
    """
    modules = []

    if not template_commands_dir.exists():
        return modules

    for file in template_commands_dir.glob("*_commands.py.jinja"):
        # e.g. "dist_commands.py.jinja" -> "dist_commands"
        module_name = file.stem.replace(".py", "")
        import_line = f"from .{module_name} import commands as {module_name}"
        modules.append((module_name, import_line))

    return sorted(modules)  # Sort for consistent ordering


def main():
    if len(sys.argv) < 2:
        print("Usage: patch_commands_init_py.py <app_name> [template_root]")
        sys.exit(1)

    app_name = sys.argv[1]
    init_path = Path(app_name) / "commands" / "__init__.py"

    # Template root directory (for discovering modules)
    if len(sys.argv) >= 3:
        template_root = Path(sys.argv[2])
    else:
        # Default: look relative to this script (script is in ops/copier/)
        template_root = Path(__file__).parent.parent.parent

    # The commands directory in the template uses {{app_name}} as folder name
    template_commands_dir = template_root / "{{app_name}}" / "commands"

    if not init_path.exists():
        print(f"[skip] {init_path} does not exist")
        return

    content = init_path.read_text()
    original_content = content

    # Discover command modules from template
    imports_to_add = discover_command_modules(template_commands_dir)

    if not imports_to_add:
        print("[skip] No *_commands.py.jinja files found in template")
        return

    print(f"[info] Found {len(imports_to_add)} command modules: {[m[0] for m in imports_to_add]}")

    for module_name, import_line in imports_to_add:
        # Skip if already imported
        if import_line in content:
            print(f"[ok] {module_name} already imported")
            continue

        # Add import and extend commands
        append_block = f"\n{import_line}\ncommands += {module_name}\n"

        # Find the best place to insert (after last "commands" line)
        lines = content.rstrip().split('\n')
        insert_pos = len(lines)

        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith("commands =") or line.startswith("commands +="):
                insert_pos = i + 1
                break

        # Insert the new import block
        lines.insert(insert_pos, append_block)
        content = '\n'.join(lines)
        print(f"[patch] Added import for {module_name}")

    if content != original_content:
        init_path.write_text(content)
        print(f"[done] Updated {init_path}")
    else:
        print(f"[ok] {init_path} already up to date")


if __name__ == "__main__":
    main()
