#!/usr/bin/env python3
"""
Manage applications by creating new apps or integrating existing ones.

This script:
1. Creates new apps or links existing ones (from filesystem or git)
2. Sets up hardlinks between the apps directory and additional_apps directory
3. Automatically installs apps if they don't already exist in the bench

Usage:
	./manage_app.py create <app_name>
	./manage_app.py link <app_path_or_url>
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from urllib.parse import urlparse

# Constants
BENCH_DIR = "/home/iqa/bench"
APPS_DIR = f"{BENCH_DIR}/apps"
SITE_NAME = "iq_site"


def run_command(cmd, cwd=None, interactive=False):
	"""Run a shell command and return the output.

	If interactive is True, the command will run in interactive mode,
	allowing user input and displaying output in real-time.
	"""
	print(f"Running: {' '.join(cmd)}")

	if interactive:
		# Run in interactive mode
		try:
			process = subprocess.run(
				cmd,
				cwd=cwd,
				check=True,
				text=True,
				stdout=None,  # Use parent's stdout/stderr
				stderr=None,
				stdin=None	# Use parent's stdin for interaction
			)
			return "Command completed successfully"
		except subprocess.CalledProcessError as e:
			print(f"Error: Command failed with exit code {e.returncode}")
			sys.exit(1)
	else:
		# Run in non-interactive mode with captured output
		result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
		if result.returncode != 0:
			print(f"Error: {result.stderr}")
			sys.exit(1)
		return result.stdout.strip()


def create_symlink(source_dir, target_dir):
	"""Create symbolic link for the directory."""
	source_path = Path(source_dir)
	target_path = Path(target_dir)

	print(f"Creating symbolic link from {source_dir} to {target_dir}")

	# Remove target directory if it exists
	if target_path.exists():
		if target_path.is_symlink():
			target_path.unlink()
		else:
			shutil.rmtree(target_path)

	# Create the parent directory if it doesn't exist
	target_path.parent.mkdir(parents=True, exist_ok=True)

	# Create symbolic link for the directory
	try:
		os.symlink(source_path, target_path, target_is_directory=True)
		print(f"Symbolic link created successfully: {target_path} -> {source_path}")
	except OSError as e:
		print(f"Warning: Could not create symbolic link: {e}")
		# Fallback to copy if symlink fails
		print(f"Falling back to directory copy...")
		shutil.copytree(source_path, target_path)


def is_url(path_or_url):
	"""Check if the given string is a URL."""
	parsed = urlparse(path_or_url)
	return bool(parsed.scheme and parsed.netloc)


def is_file_path(path):
	"""Check if the given string is a file path."""
	return os.path.exists(path) or path.startswith('/') or path.startswith('~') or \
		(len(path) > 1 and path[0].isalpha() and path[1] == ':')  # Windows drive letter


def create_new_app(app_name):
	"""Create a new app."""
	print(f"Creating new app: {app_name}")

	# Create the app in interactive mode
	run_command(["bench", "new-app", app_name], cwd=BENCH_DIR, interactive=True)
	print(f"App {app_name} created.")

	print(f"Installing app {app_name}")
	run_command(["bench", "--site", "iq_site", "install-app", app_name], cwd=BENCH_DIR, interactive=True)

	print("\n\n(!) Run Task (F8) -> Restart Bench !!\n\n")


def link_existing_app(app_path_or_url):
	"""Link an existing app from filesystem or git."""
	import re
	
	# Extract module_name from git URL
	if is_url(app_path_or_url):
		# Find the repository name (between last "/" and ".git" if present)
		match = re.search(r"/([^/]+)(\.git)?$", app_path_or_url)
		if not match:
			raise ValueError(f"Invalid git URL format: {app_path_or_url}")
		
		module_name = match.group(1)
		if module_name.endswith(".git"):
			module_name = module_name[:-4]
	else:
		raise ValueError(f"Not a valid git URL: {app_path_or_url}")
	
	print(f"Loading app from '{app_path_or_url}'")
	run_command(["bench", "get-app", app_path_or_url], cwd=BENCH_DIR, interactive=True)
	
	# Read hooks.py to get app_name
	hooks_file_path = f"{APPS_DIR}/{module_name}/{module_name}/hooks.py"
	if not os.path.exists(hooks_file_path):
		raise FileNotFoundError(f"Could not find hooks.py at {hooks_file_path}")
	
	app_name = None
	with open(hooks_file_path, 'r') as hooks_file:
		for line in hooks_file:
			line = line.strip()
			if line.startswith('app_name ='):
				# Extract the app name from the line (e.g., app_name = "fcrm")
				match = re.search(r'app_name\s*=\s*["\']([^"\']+)["\']', line)
				if match:
					app_name = match.group(1)
					break
	
	if not app_name:
		raise ValueError(f"Could not find app_name in {hooks_file_path}")
	
	# Install the app
	print(f"Installing app '{app_name}'")
	run_command(["bench", "--site", SITE_NAME, "install-app", app_name], cwd=BENCH_DIR, interactive=True)

	print("\n\n(!) Run Task (F8) -> Restart Bench !!\n\n")


def main():
	parser = argparse.ArgumentParser(description="Manage applications")
	subparsers = parser.add_subparsers(dest="command", help="Command to execute")

	# Create app command
	create_parser = subparsers.add_parser("create", help="Create a new app")
	create_parser.add_argument("app_name", help="Name of the app to create")

	# Link app command
	link_parser = subparsers.add_parser("link", help="Link an existing app")
	link_parser.add_argument("app_path_or_url", help="URL to the existing app git repository")

	args = parser.parse_args()

	if args.command == "create":
		create_new_app(args.app_name)
	elif args.command == "link":
		link_existing_app(args.app_path_or_url)
	else:
		parser.print_help()
		sys.exit(1)


if __name__ == "__main__":
	main()
