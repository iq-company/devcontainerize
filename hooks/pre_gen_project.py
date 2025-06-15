import os
import sys

def fail(message):
    print(f"[ERROR] {message}")
    sys.exit(1)

project_root = os.getcwd()
devcontainer_path = os.path.join(project_root, ".devcontainer")

if os.path.exists(devcontainer_path):
    fail(".devcontainer already setup. Skipping")

# dynamisch home_dir setzen, wenn nicht manuell überschrieben
username = "{{ cookiecutter.username }}"
home_dir = "/home/{{ cookiecutter.username }}"
os.environ["HOME_DIR"] = home_dir

