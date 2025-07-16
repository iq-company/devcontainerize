#!/usr/bin/env python3
import os
import sys
import json

def find_first_nonempty_dir(dirs):
    for d in dirs:
        if os.path.isdir(d):
            try:
                # If at least one file or subdirectory exists
                if os.listdir(d):
                    return d
            except Exception as e:
                print(f"Error accessing {d}: {e}")
    return None

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def ensure_keybindings_file(path):
    if not os.path.isfile(path):
        # Create an empty JSON file with an empty array
        write_file(path, "[]\n")

def update_between_markers(content, new_block):
    """
    Replace content between marker comments while maintaining JSON structure
    and keeping the marker comments
    """
    marker_begin = "// iq shortcuts - begin"
    marker_end = "// iq shortcuts - end"

    # Find the markers
    idx_begin = content.find(marker_begin)
    if idx_begin == -1:
        return None  # Marker not found
    idx_end = content.find(marker_end, idx_begin)
    if idx_end == -1:
        return None  # End marker not found

    # Get the part before marker_begin and after marker_end+length of marker
    before = content[:idx_begin]
    after = content[idx_end + len(marker_end):]

    # Check if we're in the middle of a JSON array
    in_json_array = False
    if before.strip() and after.strip():
        if ']' in after and '[' in before:
            in_json_array = True

    # If we're in the middle of a JSON array, we need to handle formatting differently
    if in_json_array:
        # Parse the parts to see if we need a comma
        need_comma_before = False
        need_comma_after = False

        # Check if we need a comma before our content
        if before.strip() and before.strip()[-1] != '[' and before.strip()[-1] != ',':
            need_comma_before = True

        # Check if we need a comma after our content
        if after.strip() and after.strip()[0] != ']' and after.strip()[0] != ',':
            need_comma_after = True

        # Build new content with proper JSON formatting - INCLUDING marker comments
        if need_comma_before:
            new_section = f"{before.rstrip()},\n  {marker_begin}\n  {new_block.strip()}\n  {marker_end}"
        else:
            new_section = f"{before.rstrip()}\n  {marker_begin}\n  {new_block.strip()}\n  {marker_end}"

        if need_comma_after:
            new_section = f"{new_section},\n{after.lstrip()}"
        else:
            new_section = f"{new_section}\n{after.lstrip()}"

        return new_section
    else:
        # Not in a JSON array, use the old approach with marker comments
        new_section = f"{marker_begin}\n{new_block.strip()}\n{marker_end}"
        return before + new_section + after

def append_markers(content, new_block):
    """
    Insert new keybindings just before the last closing bracket of the JSON array,
    wrapped in marker comments for future updates
    """
    marker_begin = "// iq shortcuts - begin"
    marker_end = "// iq shortcuts - end"

    # Find the position of the last closing bracket
    last_bracket_pos = content.rstrip().rfind(']')

    if last_bracket_pos == -1:
        # If no closing bracket found, append at the end (fallback)
        return content

    # Insert before the last bracket
    before = content[:last_bracket_pos].rstrip()
    after = content[last_bracket_pos:]

    # Determine if we need a comma (only if there are already items in the array)
    need_comma = False
    if before.strip():
        # Look for the last non-whitespace character
        last_char = before.strip()[-1]
        # If the last character isn't an opening bracket and isn't a comma
        if last_char != '[' and last_char != ',':
            need_comma = True

    # Format properly with appropriate comma and markers
    if need_comma:
        formatted = f"{before},\n  {marker_begin}\n  {new_block.strip()}\n  {marker_end}\n{after}"
    else:
        formatted = f"{before}\n  {marker_begin}\n  {new_block.strip()}\n  {marker_end}\n{after}"

    return formatted

def prepend_prevent_comment(content):
    comment = "// iq shortcuts - prevent changes\n"
    return comment + content

def process_project_keybindings(content):
    """
    Extract only the array items from the project keybindings file,
    removing comments and outer brackets
    """
    # Remove any comments before the array
    try:
        # Try to find the start of the array
        start_idx = content.find('[')
        if start_idx == -1:
            return content  # No array found, return as is

        # Extract content from the start of the array to the end
        array_content = content[start_idx:]

        # Parse as JSON to validate and format properly
        json_content = json.loads(array_content)

        # Convert each item to a string and join with commas and newlines
        items = []
        for item in json_content:
            # Format each object with proper indentation
            item_str = json.dumps(item, indent=2)
            items.append(item_str)

        # Join all items with commas and newlines
        return ",\n  ".join(items)
    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse keybindings JSON: {e}")
        # Fallback to simple string manipulation if JSON parsing fails
        if content.strip().startswith('[') and content.strip().endswith(']'):
            return content.strip()[1:-1].strip()
        return content

def main():
    # The three possible directories (mounted in the container)
    dirs = [
        "/home/{{ cookiecutter.image_user }}/.vscode-host"
    ]
    workdir = find_first_nonempty_dir(dirs)
    if workdir is None:
        print("No VSCode user directory found. Terminating script.")
        sys.exit(0)

    keybindings_path = os.path.join(workdir, "keybindings.json")
    ensure_keybindings_file(keybindings_path)
    try:
        content = read_file(keybindings_path)
    except Exception as e:
        print(f"Error reading file {keybindings_path}: {e}")
        sys.exit(1)

    # If the "prevent changes" comment exists, exit
    if "// iq shortcuts - prevent changes" in content:
        print("Changes are disabled by prevent changes flag.")
        sys.exit(0)

    # Project keybindings from the project folder (assumed: relative path .devcontainer/.vscode/keybindings.json)
    project_keybindings_path = os.path.join(os.getcwd(), "apps", "{{ cookiecutter.app_name }}", ".devcontainer", ".vscode", "keybindings.json")
    if not os.path.isfile(project_keybindings_path):
        print(f"Project keybindings file not found: {project_keybindings_path}")
        sys.exit(0)
    try:
        project_keybindings = read_file(project_keybindings_path)
        # Process keybindings to remove outer brackets
        project_keybindings = process_project_keybindings(project_keybindings)
    except Exception as e:
        print(f"Error reading project keybindings: {e}")
        sys.exit(1)

    # Check if markers are present
    if "// iq shortcuts - begin" in content and "// iq shortcuts - end" in content:
        new_content = update_between_markers(content, project_keybindings)
        if new_content is None:
            print("Markers were not found correctly. Terminating script.")
            sys.exit(0)
        write_file(keybindings_path, new_content)
        print("Keybindings were updated (replaced between markers).")
        sys.exit(0)
    else:
        # No IQ keybindings markers exist - then ask user
        print("Extend VSCode User keybindings for this project?\n\t (Y=yes, DAA=dont ask again, (default)=no")
        choice = input().strip().lower()
        if choice == "y":
            new_content = append_markers(content, project_keybindings)
            write_file(keybindings_path, new_content)
            print("Keybindings were added (items merged directly into the keybindings array).")
        elif choice == "daa":
            new_content = prepend_prevent_comment(content)
            write_file(keybindings_path, new_content)
            print("Keybindings were not changed; prevent changes comment added.")
        else:
            print("No changes made.")
        sys.exit(0)

if __name__ == "__main__":
    main()

