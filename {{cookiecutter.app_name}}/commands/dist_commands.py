# imports - third party imports
import click
import os
import shutil
import importlib
import subprocess
import sys
import threading

# imports - module imports
import frappe
from frappe.commands import pass_context

@click.command("clear-assets-cache")
def clear_assets_cache():
	"Clears assets cache"

	frappe.init("")
	frappe.cache.delete_value("assets_json", shared=True)


@click.command("mkdocs-serve")
@click.option("--no-browser", is_flag=True, default=False, help="Prevents starting the browser")
def mkdocs_serve(no_browser=False):
	"Serve mkdocs locally"
	target_path = os.path.join(frappe.get_app_path("{{cookiecutter.app_name}}"), "mkdocs")

	print("Starting mkdocs server... will be available (soon) under http://localhost:8020")
	print("Press Ctrl+C to stop")

	# open browser
	if not no_browser:
		frappe.utils.execute_in_shell("open http://localhost:8020")

	# copy_files(os.path.join(frappe.get_app_path("{{cookiecutter.app_name}}"), "public", "images"), os.path.join(frappe.get_app_path("{{cookiecutter.app_name}}"), "mkdocs", "docs", "img", "public_doc_assets"))

	# Check if docker is available
	if shutil.which("docker"):
		# frappe.utils.execute_in_shell("docker run -it --rm -p 8020:8000 -v {0}:/docs -v {0}/../public/images:/docs/docs/img --name mkdocs squidfunk/mkdocs-material".format(target_path, target_path))
		frappe.utils.execute_in_shell("docker run -it --rm -p 8020:8000 -v {0}:/docs --name mkdocs squidfunk/mkdocs-material".format(target_path, target_path))
	elif shutil.which("mkdocs"):

		os.chdir(target_path)
		frappe.utils.execute_in_shell("mkdocs serve -a 0.0.0.0:8020")
	else:
		print("Please install docker or install mkdocs with: pip install mkdocs-material")

@click.command("mkdocs-build")
def mkdocs_build():
	"Build mkdocs documentation"
	target_path = os.path.join(frappe.get_app_path("{{cookiecutter.app_name}}"), "mkdocs")
	preprocess_mkdocs()

	print("Building mkdocs documentation in {0} ...".format(target_path))

	# copy ../public/images/* to docs/img/
	copied_files = copy_files(os.path.join(frappe.get_app_path("{{cookiecutter.app_name}}"), "public", "images"), os.path.join(frappe.get_app_path("{{cookiecutter.app_name}}"), "mkdocs", "docs", "img", "public_doc_assets"))

	# Check if docker is available
	if shutil.which("docker"):
		frappe.utils.execute_in_shell("docker run -it --rm -v {0}:/docs --user $(id -u):$(id -g) --name mkdocs squidfunk/mkdocs-material build --site-dir dist".format(target_path, target_path))
		revert_copy(copied_files)

	elif shutil.which("mkdocs"):
		# Change directory to target_path
		os.chdir(target_path)
		frappe.utils.execute_in_shell("mkdocs build --site-dir dist")

		revert_copy(copied_files)

	else:
		print("Please install mkdocs with: pip install mkdocs-material")
		return

def preprocess_mkdocs():
	if os.environ.get("LOCAL_DEV_ENV") == "true":
		if not shutil.which("mkdocs"):
			print("Installing mkdocs...")
			os.system("pip install mkdocs-material")

	import datetime
	year = datetime.datetime.now().year
	brand_name = os.getenv("IQ_BRAND_NAME", "{{cookiecutter.project_name}}")
	filename = os.path.join(frappe.get_app_path("{{cookiecutter.app_name}}"), "mkdocs", "mkdocs.yml")

	with open(filename, "r", encoding="utf-8") as file:
		lines = file.readlines()

	with open(filename, "w", encoding="utf-8") as file:
		for line in lines:
			if line.startswith("copyright:"):
				line = f'copyright: "&copy; {year} {brand_name}"\n'

			file.write(line)# replace the copyright line in mkdocs.yml

def copy_files(src_dir, dst_dir):
	"""Copy files from src_dir to dst_dir."""
	# Ensure destination directory exists
	os.makedirs(dst_dir, exist_ok=True)

	copied_files = []
	# Loop over items in the source directory
	for filename in os.listdir(src_dir):
		src_file = os.path.join(src_dir, filename)
		dst_file = os.path.join(dst_dir, filename)

		# Only copy files (skip directories)
		if os.path.isfile(src_file):
			shutil.copy2(src_file, dst_file)
			copied_files.append(dst_file)

	return copied_files

def revert_copy(dst_dir: list | str):
	"""Revert the copy operation by removing the destination directory."""

	if isinstance(dst_dir, str):
		dst_dir = [dst_dir]

	for dst_dir in dst_dir:
		if os.path.exists(dst_dir):
			if os.path.isfile(dst_dir):
				os.remove(dst_dir)
			else:
				shutil.rmtree(dst_dir)

@click.command("iq-release-dist")
def iq_release_dist():
	"""Execute release cleanup tasks defined in iq_release_cleanup hooks."""
	# Get all release cleanup tasks from all apps
	all_cleanup_tasks = []

	linked_apps = frappe.get_all_apps(False, os.path.join(frappe.utils.get_bench_path(), "sites"))

	for app_name in linked_apps:
		all_cleanup_tasks.extend(frappe.get_hooks("iq_release_cleanup", app_name=app_name))

	# check if docker is available
	during_build = False if shutil.which("docker") else True

	# Execute cleanup tasks
	for cleanup_task in all_cleanup_tasks:
		if "context" in cleanup_task and cleanup_task["context"] == "only_during_build" and not during_build:
			continue

		# Call function
		if "function" in cleanup_task:
			function_path = cleanup_task["function"]
			module_path, function_name = function_path.rsplit(".", 1)
			try:
				module = importlib.import_module(module_path)
				function = getattr(module, function_name)
				print(f"Executing function: {function_path}")
				function()
			except Exception as e:
				print(f"Error executing function {function_path}: {e}")

		# Execute bash command
		elif "bash" in cleanup_task:
			bash_command = cleanup_task["bash"]
			print(f"Executing bash command: {bash_command}")
			try:
				subprocess.run(bash_command, shell=True, check=True)
			except subprocess.CalledProcessError as e:
				print(f"Error executing bash command: {e}")

		# Execute script
		elif "script" in cleanup_task:
			# Determine which app this script belongs to
			for app_name in linked_apps:
				script_path = os.path.join(frappe.get_app_path(app_name), cleanup_task["script"])
				if os.path.exists(script_path):
					print(f"Executing script: {script_path}")
					try:
						if script_path.endswith(".py"):
							subprocess.run([sys.executable, script_path], check=True)
						else:
							subprocess.run(["bash", script_path], check=True)
					except subprocess.CalledProcessError as e:
						print(f"Error executing script: {e}")
					break


@click.command("run-iq-tests")
@click.option("--app", help="Specify app to run tests for")
@click.option("--module", help="Specify module to run tests for")
@click.option("--doctype", help="Specify doctype to run tests for")
@click.option("--test", help="Specify test function to run")
@click.option("--section", help="Specify test section for visual grouping")
@click.option("--skip-on-first-error/--continue-on-error", default=True, help="Stop testing on first error or continue through all tests")
@pass_context
def run_iq_tests(context, app=None, module=None, doctype=None, test=None, section=None, skip_on_first_error=True):
	"""Run IQ enabled tests """
	site_name = context.sites[0] if context.sites else None
	if not site_name:
		raise frappe.SiteNotSpecifiedError

	frappe.init(site=site_name)

	# Divider line for better visibility
	app_divider = "\n" + "=" * 80 + "\n{:^80}\n" + "=" * 80
	section_divider = "\n" + "-" * 60 + "\n{:^60}\n" + "-" * 60
	result_divider = "\n" + "=" * 100 + "\n{:^100}\n" + "=" * 100

	# Store test results for summary
	results = {
		"passed": [],
		"failed": []
	}

	installed_apps = frappe.get_installed_apps()

	for app_name in installed_apps:
		# Skip app if filter is provided and doesn't match
		if app and app != app_name:
			continue

		# Get iq_tests hooks from the current app
		app_iq_tests = frappe.get_hooks("iq_tests", app_name=app_name)

		if not app_iq_tests:
			continue

		# Print app header with clear divider
		print(app_divider.format(f" TESTS FOR APP: {app_name.upper()} "))

		for test_section in app_iq_tests:
			# Only run specific section if requested
			if section and test_section.get("section") != section:
				continue

			# Print section header with divider for better visualization
			section_name = test_section.get("section", "Unnamed section")
			print(section_divider.format(f" SECTION: {section_name} "))

			for step in test_section.get("steps", []):
				run_cmd = f"bench --site {frappe.local.site} run-tests"
				test_params = []
				step_descriptor = ""

				# Add app as first parameter
				test_params.append(f"--app {app_name}")

				if "doctype" in step:
					test_doctype = step["doctype"]
					# Skip if doctype filter doesn't match
					if doctype and doctype != test_doctype:
						continue

					test_params.append(f"--doctype \"{test_doctype}\"")
					step_descriptor = f"DocType: {test_doctype}"

				elif "module" in step:
					# Skip if module filter doesn't match
					if module and module != step["module"]:
						continue

					module_path = step["module"]
					test_params.append(f"--module {module_path}")
					step_descriptor = f"Module: {module_path}"

					# Add individual tests if specified
					if "tests" in step:
						test_args = []
						for test_name in step["tests"]:
							# Skip if test filter doesn't match
							if test and test != test_name:
								continue
							test_args.append(f"--test {test_name}")
							step_descriptor += f", Test: {test_name}"

						if test_args:
							test_params.extend(test_args)

				# Always add --skip-test-records parameter as the last parameter
				test_params.append("--skip-test-records")

				# Construct full command
				full_cmd = f"{run_cmd} {' '.join(test_params)}"

				# Show command being executed with clear formatting
				print(f"\n> EXECUTING: {full_cmd}\n")

				# Execute with live output and capture for analysis
				# Credit: https://stackoverflow.com/a/4417735

				# We'll capture output while also displaying it
				def reader_thread(pipe, queue):
					try:
						with pipe:
							for line in iter(pipe.readline, b''):
								line_str = line.decode('utf-8')
								queue.append(line_str)
								print(line_str, end='', flush=True)
					finally:
						pass

				process = subprocess.Popen(
					full_cmd,
					shell=True,
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					bufsize=1
				)

				# Create lists to store output lines
				stdout_lines = []
				stderr_lines = []

				# Start threads to process output
				stdout_thread = threading.Thread(target=reader_thread, args=[process.stdout, stdout_lines])
				stderr_thread = threading.Thread(target=reader_thread, args=[process.stderr, stderr_lines])
				stdout_thread.start()
				stderr_thread.start()

				# Wait for the process to complete
				return_code = process.wait()

				# Wait for output threads to complete
				stdout_thread.join()
				stderr_thread.join()

				# Combine output for analysis
				stdout = ''.join(stdout_lines)
				stderr = ''.join(stderr_lines)
				output = stdout + stderr

				# Check for failure indicators in the output
				has_failure = return_code != 0 or "FAILED" in output or "FAIL:" in output or "ERROR:" in output or "Traceback" in output or "AssertionError" in output

				test_result = {
					"app": app_name,
					"section": section_name,
					"step": step_descriptor,
					"command": full_cmd,
					"return_code": return_code,
					"output": output
				}

				if not has_failure:
					results["passed"].append(test_result)
					print(f"\n✅ PASSED: {step_descriptor}")
				else:
					results["failed"].append(test_result)
					print(f"\n❌ FAILED: {step_descriptor}")

					# Stop testing on first error if enabled
					if skip_on_first_error:
						print("\nStopping tests due to error. Use --continue-on-error to run all tests regardless of failures.")
						break

				# Add a separator after each step
				print("\n" + "-" * 40)

			# If we broke out of the step loop due to a failure, break out of the section loop too
			if skip_on_first_error and results["failed"]:
				break

		# If we broke out of the section loop due to a failure, break out of the app loop too
		if skip_on_first_error and results["failed"]:
			break

	# Print summary of results
	print(result_divider.format(" TEST RESULTS SUMMARY "))

	if results["passed"]:
		print(f"\n✅ PASSED TEST UNITS: {len(results['passed'])}")
		for i, result in enumerate(results["passed"], 1):
			print(f"  {i}. App: {result['app']}, Section: {result['section']}, {result['step']}")

	if results["failed"]:
		print(f"\n❌ FAILED TESTS: {len(results['failed'])}")
		for i, result in enumerate(results["failed"], 1):
			print(f"  {i}. App: {result['app']}, Section: {result['section']}, {result['step']}")
			print(f"     Command: {result['command']}")
			print(f"     Return Code: {result['return_code']}")

			# Print relevant failure details from the output
			if "output" in result:
				failure_lines = []
				for line in result["output"].split("\n"):
					if any(pattern in line for pattern in ["FAILED", "FAIL:", "ERROR:", "Traceback", "AssertionError"]):
						failure_lines.append(line)

				if failure_lines:
					print("\n     Failure details:")
					for line in failure_lines[:5]:  # Limit to 5 most relevant lines
						print(f"       {line.strip()}")
					if len(failure_lines) > 5:
						print(f"       ... and {len(failure_lines)-5} more error lines")

	# Return error code if any tests failed
	if results["failed"]:
		print("\n🛑 Some tests failed. See above for details.")
		sys.exit(1)
	elif not (results["passed"] or results["failed"]):
		print("\n⚠️ No tests were run!")
		sys.exit(0)
	else:
		print(f"\n✅ All {len(results['passed'])} tests passed successfully!")
		sys.exit(0)
