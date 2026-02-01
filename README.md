# Frappe Devcontainerize Template

A `copier`-based template for creating devcontainerized Frappe app projects with Docker build automation.

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Configuration Options](#configuration-options)
- [CLI Commands](#cli-commands)
- [Devcontainer](#devcontainer)
- [Environment Files](#environment-files)
- [Keeping Updated](#keeping-updated)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Install copier

```bash
pipx install copier
# or
pip install copier
```

### 2. Create a new project

```bash
# Navigate to your app directory
cd ~/apps/my_frappe_app

# Run copier
copier copy gh:iq-company/devcontainerize . --trust

# Or with predefined answers
copier copy gh:iq-company/devcontainerize . --data-file=copier-answers.yml --trust
```

### 3. Build and run

When `feature_image_creation` is enabled (default), copier automatically:
1. Adds `baker-cli` to your `pyproject.toml` dev dependencies
2. Runs `pip install -e ".[dev]"` to install it

You can then build Docker images:
```bash
bench ops build plan           # Show what would be built
bench ops build images         # Build images
bench ops build images --push  # Build and push to registry
```

If the automatic installation fails, run manually:
```bash
pip install -e ".[dev]"
```

---

## Features

| Feature | Description | Default |
|---------|-------------|---------|
| `feature_devcontainer` | VSCode Dev Containers support | `true` |
| `feature_image_creation` | Dockerfile generation | `true` |
| `feature_mkdocs` | MkDocs documentation generation | `true` |

### Core Features

- **Reproducible Dev Environment**: Consistent environment for all developers using VSCode Dev Containers
- **Multi-Stage Docker Builds**: Optimized for speed and size with 4 stages (base, builder, dev, release)
- **Database Flexibility**: Support for PostgreSQL, MariaDB, and SQLite (TODO)
- **Build Automation**: `baker-cli` for Docker builds with checksummed tags and smart caching
- **CLI Management**: `bench ops` for template updates, version management, and releases
- **MkDocs Integration**: Built-in documentation generation with `bench mkdocs-build`

---

## Architecture

```
Docker Build Pipeline
=====================

┌─────────────┐
│ Dockerfile. │
│    base     │──────┐
└─────────────┘      │
      │              │
      ▼              │
┌─────────────┐      │
│ Dockerfile. │      │
│   builder   │      │
└─────────────┘      │
      │              │
      ▼              │
┌─────────────┐      │
│ Dockerfile. │◄─────┘
│     dev     │
└─────────────┘
      │
      ▼
┌─────────────┐
│ Dockerfile. │
│   release   │
└─────────────┘
```

### Stage Description

| Stage | Purpose | Base Image | Size |
|-------|---------|------------|------|
| **base** | Runtime dependencies (Python, Node, wkhtmltopdf, nginx configs) | `python:3.12-slim-bookworm` | ~500MB |
| **builder** | Compilation tools (gcc, make, cmake, psql, nginx) for building pg client and nginx with less deps | `base` | ~1.5GB |
| **dev** | Full development environment with Frappe bench | `base` + `builder` | ~2GB |
| **release** | Production-ready, cleaned image | `base` | ~800MB |
| **release-alpine** | TODO: Minimal worker image (experimental) | `python:3.12-alpine` | ~300MB |

---

## Project Structure

```
app/
├── .devcontainer/                 # VSCode devcontainer config
│   ├── devcontainer.json
│   ├── compose.dev.override.yml
│   └── honcho/
│       ├── Procfile
│       ├── Procfile_skip_web
│       └── Procfile_skip_worker
├── ops/
│   ├── build/                     # Image creation
│   │   ├── docker/                # Dockerfiles
│   │   │   ├── Dockerfile.base
│   │   │   ├── Dockerfile.builder
│   │   │   ├── Dockerfile.dev
│   │   │   └── Dockerfile.release
│   │   ├── resources/             # Files copied into images
│   │   │   ├── container-reduce.sh
│   │   │   ├── setup_bench_apps.py
│   │   │   ├── nginx/
│   │   │   └── gunicorn/
│   │   ├── build-settings.yml     # baker-cli config
│   │   ├── .copier-answers.yml    # Copier answers
│   │   └── VERSION                # Semantic version
│   ├── compose/                   # Docker Compose files
│   │   ├── compose.base.yml
│   │   ├── compose.postgres.yml
│   │   ├── compose.mariadb.yml
│   │   ├── compose.release.yml
│   │   └── .env                   # Generated (not in Git)
│   ├── env/                       # Environment templates
│   │   ├── .env.template
│   │   └── .env.*.addon.template
│   ├── scripts/
│   │   ├── devcontainer/          # Host-side devcontainer scripts
│   │   │   ├── init_env_files
│   │   │   ├── init_env_files.ps1
│   │   │   └── create_app.sh
│   │   ├── runtime/               # Container runtime scripts
│   │   │   ├── init_site.sh
│   │   │   ├── check_and_setup_pth_files.sh
│   │   │   ├── check_iq_keybindings.py
│   │   │   ├── install_iq_keybindings.py
│   │   │   └── info_bench_start.sh
│   │   ├── release/               # Host-side release scripts
│   │   │   ├── run_release_helper.sh
│   │   │   ├── stop_release_helper.sh
│   │   │   └── clean_release_helper.sh
│   │   └── common/                # Common utilities
│   │       └── manage_app.py
│   └── copier/                    # Copier tasks (not copied to target)
│       ├── patch_commands_init_py.py
│       ├── patch_pyproject_toml.py
│       └── update_feature_skips.py
└── {{ app_name }}/
    └── commands/
        ├── __init__.py
        ├── dist_commands.py       # Distribution commands
        └── ops_commands.py        # bench ops CLI
```

---

## Configuration Options

### copier.yaml Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `app_name` | string | (from directory) | Your Frappe app name |
| `project_name` | string | "My Awesome App" | Human-readable project name |
| `project_slug` | string | `app_name` | URL/docker-safe name |
| `image_prefix` | string | `project_slug` | Docker image prefix |
| `default_dbms` | choice | `postgres` | Database: postgres, mariadb, sqlite |
| `frappe_branch` | string | `version-15` | Frappe branch name |
| `frappe_tag` | string | `""` | Frappe tag (optional, overrides branch) |
| `frappe_commit` | string | `""` | Frappe commit SHA (optional, overrides all) |
| `image_user` | string | `frappe` | Docker container user |
| `image_group` | string | `frappe` | Docker container group |
| `site_name` | string | `app_name.local` | Development site domain |

---

## CLI Commands

### bench ops

The `bench ops` CLI provides commands for template updates, builds, and maintenance.

```bash
# Template Update
bench ops update                # Update from template
bench ops update --dry          # Preview changes (dry run)
bench ops update --force        # Force overwrite local changes

# Version Management
bench ops version               # Show current version
bench ops version --bump        # Bump bugfix version (default)
bench ops version --bump --major    # Bump major version
bench ops version --bump --feature  # Bump feature version
bench ops version --bump --commit   # Bump and commit

# Build (wrapper for baker-cli)
bench ops build                 # Show build plan (default)
bench ops build --images        # Build Docker images
bench ops build --images --push # Build and push to registry
bench ops build --images --force # Force rebuild

# Testing
bench ops test                  # Run all tests
bench ops test --app my_app     # Run tests for specific app
bench ops test --section Auth   # Run tests for specific section

# Release Environment
bench ops release run           # Start release containers
bench ops release stop          # Stop release containers
bench ops release clean         # Remove containers and volumes
```

### baker-cli (Direct)

For more advanced build operations:

```bash
baker plan                      # Show full build plan
baker build --targets dev       # Build specific targets
baker build --force             # Force rebuild
baker rm --targets dev          # Remove local images
```

---

## Devcontainer

### Prerequisites

- Docker with docker-compose
- VSCode with Dev Containers extension

### Getting Started

1. Open the project folder in VSCode
2. Press `Ctrl+Shift+P` and select "Dev Containers: Reopen in Container"
3. Wait for the container to build and start

### Procfile Variants

| File | Description |
|------|-------------|
| `Procfile` | Full stack (web, worker, watch, schedule) |
| `Procfile_skip_web` | Without web server (for debugging) |
| `Procfile_skip_worker` | Without background workers |

---

## Environment Files

### Templates (committed to Git)

| File | Purpose |
|------|---------|
| `ops/env/.env.template` | Main configuration template |
| `ops/env/.env.*.addon.template` | DBMS-specific additions |

### Generated Files (not in Git)

| File | Purpose |
|------|---------|
| `ops/compose/.env` | Full runtime configuration |
| `.devcontainer/.env` | Minimal config for starting devcontainer from host |

### Initialization

```bash
# Initialize environment for PostgreSQL
./ops/scripts/devcontainer/init_env_files postgres

# Or for MariaDB
./ops/scripts/devcontainer/init_env_files mariadb

# Or for SQLite
./ops/scripts/devcontainer/init_env_files sqlite

# Using environment variable
DBMS=postgres ./ops/scripts/devcontainer/init_env_files
```

### Key Variables

| Variable | Description |
|----------|-------------|
| `DBMS` | Database type (postgres, mariadb, sqlite) |
| `DB_HOST` | Database host |
| `DB_PORT` | Database port |
| `DB_ROOT_PASSWORD` | Database root password |
| `DB_SUPER_USER` | Super user for DDL operations |
| `IQ_SITE_NAME` | Frappe site name |
| `NGINX_PORT` | Port for web access (default: 8010) |

---

## Keeping Updated

### Template Source Storage

After running `copier copy`, the template source is automatically moved to `ops/build/.copier-answers.yml`:

```yaml
# Auto-generated - DO NOT EDIT MANUALLY
_src_path: gh:iq-company/devcontainerize  # or local path or own fork
_commit: abc123...
app_name: my_app
feature_image_creation: true
# ... all other settings
```

This keeps the root directory clean. The `bench ops template update` command automatically uses this location.

### Update Commands

```bash
# Preview changes (dry-run)
bench ops update --dry

# Apply updates
bench ops update

# Force update (overwrite local changes)
bench ops update --force
```

**Note**: Always use `bench ops update` instead of calling `copier update` directly. The CLI handles:
- Locating the answers file in `ops/build/`
- Automatically adding `--trust`
- Moving the updated answers file back to `ops/build/`

### Automatic Post-Update Tasks

When `feature_image_creation` is enabled, copier automatically:
1. **Patches `pyproject.toml`**: Adds `baker-cli` to dev dependencies
2. **Installs dependencies**: Runs `pip install -e ".[dev]"`

### Files That Won't Be Overwritten

- `{{ app_name }}/commands/__init__.py` - Your custom commands
- `ops/env/.env.template` - Your environment configuration
- `pyproject.toml` - Your project configuration (only patched, never replaced)

---

## Troubleshooting

### Docker Build Issues

**Problem**: Build fails with permission errors
```bash
# Fix: Ensure Docker socket permissions
sudo usermod -aG docker $USER
newgrp docker
```


### Common Commands

```bash
# Inside devcontainer
bench --site SITE migrate      # Run migrations

# Outside container
bench ops build plan           # Show build plan
bench ops build images         # Build images
```

---

## License

MIT License - See LICENSE file for details.
