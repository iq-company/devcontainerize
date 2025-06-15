# Make IQ Apps developable with vscode devcontainers

Generates dockerfiles and a devcontainers setup in a frappe app with all dependencies and automated site-handling for fast development
and release builds.

Be sure you are in the app/repo directors (below bench/apps/YOUR_APP) and have venv active (`source ../../venv/bin/activate` if not).
```bash
pip install cookiecutter
cookiecutter gh:iq-company/devcontainerize
```
