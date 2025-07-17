import os

# dynamisch home_dir setzen, wenn nicht manuell überschrieben
username = "{{ cookiecutter.username }}"
home_dir = "/home/{{ cookiecutter.username }}"
os.environ["HOME_DIR"] = home_dir
