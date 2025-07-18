import sys
from pathlib import Path

app_name = sys.argv[1]
init_path = Path(app_name) / "commands" / "__init__.py"

if not init_path.exists():
    print(f"[patch] {init_path} does not exist, skipping patch.")
    sys.exit(0)

with open(init_path, "r") as f:
    lines = f.readlines()

import_line = "from .dist_commands import commands as dist_commands"
append_line = "commands += dist_commands\n"

import_exists = any(import_line in l for l in lines)

modified = False

# 1. Add import if missing
if not import_exists:
    modified = True
    print("[patch] Added import for dist_commands")

    append_line = "\n" + import_line + "\n" + append_line  # Ensure new line before appending

    # 2. Append command
    for i, line in reversed(list(enumerate(lines))):
        if line.strip().startswith("commands ="):
            lines.insert(i + 1, append_line)
            modified = True
            print("[patch] Appended dist_commands to commands")
            break
    else:
        # fallback: just append at end
        lines.append("\n" + append_line)
        print("[patch] commands = ... not found. Appended dist_commands at EOF")

if modified:
    with open(init_path, "w") as f:
        f.writelines(lines)
