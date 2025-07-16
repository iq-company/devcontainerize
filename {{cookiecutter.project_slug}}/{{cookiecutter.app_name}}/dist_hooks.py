# hooks.py extensions for the injected app

# TODO: Include it via python: import {{cookiecutter.app_name}}.dist_hooks

# Test Hooks - groups of tests to run in ci with `make test` or `bench run-iq-tests`
# --------------------------------
iq_tests = [
    # {
    #     "section": "Section Name",
    #     "steps": [
    #         # {"doctype": "Doctype Name"},
    #         {"module": "{{cookiecutter.app_name}}.docty_name.test_doctype_name"},
    #         # {"module": "{{cookiecutter.app_name}}.docty_name.test_doctype_name", "tests": ["test_fn_definition"]}
    #     ]
    # }
]

# Release cleanup hooks - clean up tasks before release
iq_release_cleanup = [
	# {"function": "{{cookiecutter.app_name}}.utils.release_cleanup.remove_dev_dependencies"},
	{"bash": "find /home/{{cookiecutter.image_user}}/bench -name '*.pyc' -delete"},
	{"script": "../delivery/resources/container-reduce.sh"},
	{"bash": "rm -rf /home/{{cookiecutter.image_user}}/bench/apps/{{cookiecutter.app_name}}/delivery", "context": "only_during_build"},
	# for now remove sqlalchemy due to cves; will be necessary later for e.g. pandas
	{"bash": "rm -rf env/lib/python3.12/site-packages/sqlalchemy*"},
]
