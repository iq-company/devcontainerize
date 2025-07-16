#!/usr/bin/env python3
"""
Setup script for installing Bench and custom apps for IQ Flow.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse


def run_command(cmd: List[str], cwd: str = None) -> None:
	"""Run a shell command with proper error handling."""
	try:
		subprocess.run(cmd, check=True, cwd=cwd)
	except subprocess.CalledProcessError as e:
		print(f"Error executing command: {' '.join(cmd)}")
		print(f"Exit code: {e.returncode}")
		sys.exit(e.returncode)


def setup_github_credentials(github_user: str, github_token: str) -> Optional[Path]:
	"""
	Set up GitHub credentials in .netrc file if token is provided.
	Returns the path to the .netrc file or None if no token was provided.
	"""
	if not github_token:
		return None

	netrc_path = Path.home() / ".netrc"
	with open(netrc_path, "w") as f:
		f.write(f"machine github.com login {github_user} password {github_token}\n")

	# Make sure the permissions are correct
	os.chmod(netrc_path, 0o600)

	return netrc_path


def cleanup_github_credentials(netrc_path: Optional[Path]) -> None:
	"""Remove GitHub credentials file if it exists."""
	if netrc_path and netrc_path.exists():
		netrc_path.unlink()


def parse_app_url(app_url: str) -> tuple:
	"""
	Parse an app URL to extract app name and branch.
	Returns (app_name, url, branch)
	"""
	# Check if URL has a branch specified
	branch = None
	if "#" in app_url:
		app_url, branch = app_url.split("#", 1)

	# Determine app name
	if app_url.startswith("https:"):
		# Extract repo name from URL
		parsed_url = urlparse(app_url)
		app_name = os.path.basename(parsed_url.path)
		if app_name.endswith(".git"):
			app_name = app_name[:-4]
	elif app_url.startswith("/"):
		# Local path - use directory name
		app_name = os.path.basename(app_url)
	else:
		# Assume app_url is in format app_name:url or just app_name
		if ":" in app_url:
			app_name, app_url = app_url.split(":", 1)
		else:
			app_name = app_url

	return app_name, app_url, branch


def main():
	parser = argparse.ArgumentParser(description="Set up bench with custom apps")
	parser.add_argument("--frappe-branch", default="version-15", help="Frappe branch to use")
	parser.add_argument("--frappe-path", default="https://github.com/frappe/frappe", help="Frappe repository URL")
	parser.add_argument("--custom-apps", default="", help="Comma-separated list of custom app URLs to install")
	parser.add_argument("--home-dir", default="/home/{{ cookiecutter.image_user }}", help="Home directory where bench will be installed")
	parser.add_argument("--github-user", default="x-oauth-basic", help="GitHub username for authentication")
	parser.add_argument("--github-token", default="", help="GitHub token for authentication")
	args = parser.parse_args()

	# Setup GitHub credentials if token is provided
	netrc_path = setup_github_credentials(args.github_user, args.github_token)

	try:
		home_dir = Path(args.home_dir)
		bench_dir = home_dir / "bench"

		# If bench directory already exists, remove it completely to start with a clean state
		if os.path.exists(bench_dir):
			print(f"Removing existing bench directory: {bench_dir}")
			shutil.rmtree(str(bench_dir))

		tmp_app_dir = Path("/opt/apps/iq_core")

		# Create temporary directories
		tmp_bench_dir = Path("/tmp/bench")
		tmp_bench_apps_dir = tmp_bench_dir / "apps"
		tmp_bench_sites_dir = tmp_bench_dir / "sites"

		os.makedirs(tmp_bench_apps_dir, exist_ok=True)
		os.makedirs(tmp_bench_sites_dir, exist_ok=True)

		# Create apps.txt file
		with open(tmp_bench_sites_dir / "apps.txt", "w") as f:
			pass

		# Clone Frappe
		run_command([
			"git", "clone", "--depth", "1", 
			"--branch", args.frappe_branch, 
			args.frappe_path, 
			str(tmp_bench_apps_dir / "frappe")
		])

		# Run Frappe patches
		run_command(["bash", str(tmp_app_dir / "delivery" / "resources" / "frappe-patches.sh")], cwd=str("/home/${IMAGE_USER}"))

		# Initialize bench
		run_command([
			"bench", "init",
			"--clone-from", str(tmp_bench_dir),
			"--clone-without-update",
			"--no-procfile", 
			"--no-backups",
			"--skip-redis-config-generation",
			"--skip-assets",
			"--verbose",
			str(bench_dir)
		])

		# Activate virtual environment and install requirements
		env_bin_dir = bench_dir / "env" / "bin"
		run_command([
			str(env_bin_dir / "pip"), "install", "frappe-bench", "oneagent-sdk"
		], cwd=str(bench_dir))

		# Create common site config
		with open(bench_dir / "sites" / "common_site_config.json", "w") as f:
			f.write("{}")

		# Remove temp bench directory
		shutil.rmtree(tmp_bench_dir)

		# Write frappe to apps.txt
		with open(bench_dir / "sites" / "apps.txt", "w") as f:
			f.write("frappe\n")

		# Process custom apps
		app_urls = ["/opt/apps/iq_core"]

		if args.custom_apps:
			app_urls.extend(args.custom_apps.split(","))

		print(f"Installing apps: {app_urls}")

		for app_url in app_urls:
			print(f"Processing app: {app_url}")
			app_name, url, branch = parse_app_url(app_url)

			if app_url.startswith("/"):
				# Local app path
				print(f"Installing local app {app_name} from {app_url}")
				app_dir = bench_dir / "apps" / app_name
				shutil.move(app_url, str(bench_dir / "apps"))

				# Add to apps.txt
				with open(bench_dir / "sites" / "apps.txt", "a") as f:
					f.write(f"{app_name}\n")
			else:
				# Remote repository
				if branch:
					print(f"Installing app {app_name} from {url} (branch: {branch})")
					run_command([
						"bench", "get-app", url, 
						"--branch", branch, 
						"--skip-assets"
					], cwd=str(bench_dir))
				else:
					print(f"Installing app {app_name} from {url}")
					run_command([
						"bench", "get-app", url
					], cwd=str(bench_dir))

			# Update common_site_config.json to add app to install_apps
			config_path = bench_dir / "sites" / "common_site_config.json"
			with open(config_path, "r") as f:
				config = json.load(f)

			# Initialize install_apps if it doesn't exist
			if "install_apps" not in config:
				config["install_apps"] = []

			# Add app to install_apps
			if app_name not in config["install_apps"]:
				config["install_apps"].append(app_name)

			# Write updated config
			with open(config_path, "w") as f:
				json.dump(config, f)

		# Run iq_core patches
		run_command(["bash", str(bench_dir / "apps" / "iq_core" / "delivery" / "resources" / "iq_core-patches.sh")], cwd=str(home_dir))

		# Setup requirements and build assets
		run_command(["bench", "setup", "requirements", "--python"], cwd=str(bench_dir))
		run_command(["bench", "setup", "requirements", "--node"], cwd=str(bench_dir))
		run_command(["bench", "build", "--production", "--apps", "frappe,iq_core"], cwd=str(bench_dir))

		# Handle assets directory
		sites_assets_dir = bench_dir / "sites_assets"
		assets_dir = bench_dir / "sites" / "assets"

		# Move and symlink assets
		shutil.move(str(assets_dir), str(sites_assets_dir))
		os.symlink(str(sites_assets_dir), str(assets_dir))

		# Create extension_paths.pth
		extension_path = bench_dir / "env" / "lib" / "python3.12" / "site-packages" / "extension_paths.pth"
		with open(extension_path, "w") as f:
			f.write(f"{bench_dir}/sites/extensions/pip_packages")

		# Clean up .git, .github, .cache directories
		for pattern in [".git", ".github", ".cache", ".config", ".yarn"]:
			for path in Path(bench_dir / "apps").glob(f"**/{pattern}"):
				if path.is_dir():
					shutil.rmtree(path)

	finally:
		# Always clean up the .netrc file
		cleanup_github_credentials(netrc_path)

if __name__ == "__main__":
	main()

