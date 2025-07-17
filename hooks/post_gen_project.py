import os
import subprocess
import sys

def run_bash(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def fail(message):
    print(f"[ERROR] {message}")
    sys.exit(1)

if __name__ == "__main__":
    # `cookiecutter` starts in the output dir of the generated project

    # devcontainer_path = os.path.join(project_root, ".devcontainer")
    # if os.path.exists(devcontainer_path):
    #     fail(".devcontainer already setup. Skipping")

    # current_dir = os.path.abspath(os.path.curdir)
    project_root = os.getcwd()
    tmp_app_dir = os.path.join(project_root, "_tmp_app_name_source")
    target_app_dir = os.path.join(project_root, "{{cookiecutter.app_name}}")
    run_bash(f"mv {os.path.join(tmp_app_dir, '*.py')} {target_app_dir}")
    run_bash(f"mv {os.path.join(tmp_app_dir, 'commands/*')} {os.path.join(target_app_dir, 'commands')}")


    # dynamisch home_dir setzen, wenn nicht manuell überschrieben
    username = "{{ cookiecutter.username }}"
    home_dir = "/home/{{ cookiecutter.username }}"
    os.environ["HOME_DIR"] = home_dir

