# {{ cookiecutter.project_name }} - Devcontainerized

This project has been set up with a devcontainer environment for Frappe app development, based on the `devcontainerize` cookiecutter template.

## Quick Start

1.  Open this project in VS Code.
2.  When prompted, click "Reopen in Container".
3.  Wait for the container to build and start.
4.  Your Frappe app `{{ cookiecutter.app_name }}` will be available at `http://localhost:8010`.

## Features

-   **Reproducible Dev Environment:** A consistent environment for all developers.
-   **Multi-Stage Docker Builds:** Optimized for speed and size.
-   **Makefile Orchestration:** Easy commands for building and managing the environment (`make dev`, `make release`, `make run-release`).
-   **Profile-Based Services:** Enable optional services like DDL mode via the `COMPOSE_PROFILES` variable in `.env`.
-   **Flexible Release Management:** Use `make run-release ENV_FILE=path/to/your.env` to test with different configurations.

For more details, see the documentation in `iq_core/mkdocs/docs/docker_setup.md` (this path should be updated).