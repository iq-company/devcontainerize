# Frappe Devcontainerize Template

A `copier`-based template for creating devcontainerized Frappe app projects.

## 🚀 Quick Start: Creating a New Project

To create a new project from this template, follow these steps.

---

## 🔧 Install `copier`

    If you don't have it already, install `copier`. It's recommended to use `pipx` to install it globally, but `pip` works too:

    ```bash
    pipx install copier
    # or
    pip install copier
    ```

##  **Create the project**

    From your desired project root directory (e.g. ~/apps/my_app), run:

    ```bash
    copier copy gh:iq-company/devcontainerize .

    # or with predefined values.yml: `copier copy gh:iq-company/devcontainerize . --data-file=copier-answers.yml`
    ```

    You will be prompted for values like app_name, which is used to place files in the correct structure (e.g. `<app_name>/commands/dist_commands.py`).

    💡 By default, the app name is automatically derived from the current working directory.

## Keeping the Project Updated

This project was generated from a template using `cruft`. To update your project with the latest changes from the template, follow these steps:

1.  Make sure you have `cruft` installed:
    ```bash
    pip install copier
    ```

2.  Commit any local changes. copier prefers a clean working tree.

3.  Run the update command:
    ```bash
    copier update
    ```

4.  If the template has changed parts you modified locally, copier will show a diff and let you choose what to keep or overwrite.

## Features

-   **Reproducible Dev Environment:** A consistent environment for all developers.
-   **Multi-Stage Docker Builds:** Optimized for speed and size.
-   **Makefile Orchestration:** Easy commands for building and managing the environment (`make dev`, `make release`, `make run-release`).
-   **Profile-Based Services:** Enable optional services like DDL mode via the `COMPOSE_PROFILES` variable in `.env`.
-   **Flexible Release Management:** Use `make run-release ENV_FILE=path/to/your.env` to test with different configurations.

## Tips

- You can use `--pretend`, `--diff`, or `--force` with `copier update` for more control.

- Files like commands/dist_command.py will be updated automatically, while other parts (e.g. user-written commands) remain untouched.

- Initialization-only files (like __init__.py) are marked to be created once and skipped on update.
