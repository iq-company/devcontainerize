# Frappe Devcontainerize Template

A `cruft`-compatible cookiecutter template for creating devcontainerized Frappe app projects.

## Quick Start: Creating a New Project

To create a new project from this template, follow these steps.

##  **Install `cruft`**

    If you don't have it already, install `cruft`. It's recommended to use `pipx` to install it globally, but `pip` works too.

    ```bash
    pipx install cruft
    # or
    pip install cruft
    ```

##  **Create the project**

    Run the `cruft create` command with the URL of this template. You will be prompted for values like project name, app name, etc.

    ```bash
    cruft create https://github.com/iq-company/devcontainerize
    ```

## Keeping the Project Updated

This project was generated from a template using `cruft`. To update your project with the latest changes from the template, follow these steps:

1.  Make sure you have `cruft` installed:
    ```bash
    pip install cruft
    ```

2.  Commit any local changes you have made to your project. `cruft` will not proceed if you have uncommitted changes.

3.  Run the update command:
    ```bash
    cruft update
    ```

4.  `cruft` will create a `.rej` file for any changes that couldn't be merged automatically. You will need to resolve these conflicts manually. After resolving, you can delete the `.rej` files.

## Features

-   **Reproducible Dev Environment:** A consistent environment for all developers.
-   **Multi-Stage Docker Builds:** Optimized for speed and size.
-   **Makefile Orchestration:** Easy commands for building and managing the environment (`make dev`, `make release`, `make run-release`).
-   **Profile-Based Services:** Enable optional services like DDL mode via the `COMPOSE_PROFILES` variable in `.env`.
-   **Flexible Release Management:** Use `make run-release ENV_FILE=path/to/your.env` to test with different configurations.

