# Frappe Devcontainerize Template

A `copier`-based template for creating devcontainerized Frappe app projects with Docker build automation.

## Table of Contents

- [Quick Start](#-quick-start)
- [Features](#-features)
- [Architecture](#-architecture)
- [Configuration Options](#-configuration-options)
- [Build Tools](#-build-tools)
- [Devcontainer](#-devcontainer)
- [Keeping Updated](#-keeping-updated)
- [Troubleshooting](#-troubleshooting)

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
baker plan                    # Show what would be built
baker build --targets dev     # Build dev image
baker build --targets release # Build release image
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

### Alpine Worker Image (Experimental)

The `release-alpine` image is a minimal Alpine-based image for worker-only deployments:

**Advantages:**
- ~60% smaller than the Debian-based release image (~300MB vs ~800MB)
- Faster container startup
- Reduced attack surface

**Limitations:**
- No wkhtmltopdf (PDF generation not supported)
- No nginx (requires external reverse proxy)
- Some Python packages may need recompilation

**Use Cases:**
```bash
# Build Alpine worker image
baker build --targets release-alpine

# Scale workers with Alpine image
docker-compose -f compose.yml up -d --scale queue-long=3
```

**Recommended deployment pattern:**
```
┌─────────────────┐     ┌─────────────────┐
│ release (full)  │     │ release-alpine  │
│ - frontend      │     │ - queue-short   │
│ - websocket     │     │ - queue-long    │
│ - scheduler     │     │ - (scalable)    │
└─────────────────┘     └─────────────────┘
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
| `frappe_version` | string | `version-15` | Frappe branch/tag |
| `image_user` | string | `frappe` | Docker container user |
| `image_group` | string | `frappe` | Docker container group |
| `site_name` | string | `app_name.local` | Development site domain |

---

## Build Tools

### baker-cli

Modern YAML-based build automation with checksummed tags and smart caching.

```bash
# Install
pip install baker-cli

# Show build plan
baker plan

# Build specific targets
baker build --targets base builder dev

# Build and push to registry
baker build --push --targets dev release

# Check what would be built (dry-run)
baker plan --check local

# Remove local images
baker rm --targets dev release
```

**Configuration**: `build-settings.yml`

Key features:
- Checksummed tags for reproducible builds
- Dependency tracking between stages
- Registry existence checks (skip builds if image exists)
- `docker buildx bake` integration

### Make Utilities

There is a `Makefile` to perform very common tasks Utility-Targets:

```bash
# Version management
make add-version                              # Interactive version bump
make add-version VERSION_COMPONENT=bugfix     # Auto bugfix bump
make add-version VERSION_COMPONENT=feature    # Auto feature bump
make add-version VERSION_COMPONENT=major COMMIT=1  # Major bump + git commit

# Testing
make test                                     # Run all tests
make test APP=my_app                          # Run tests for specific app
make test SECTION=MySection                   # Run tests for specific section
make test CONTINUE=1                          # Continue on errors

# Release environment (local testing)
make run-release ENV_FILE=./ops/env/.env      # Start release containers
make stop-release                             # Stop release containers
make clean-release                            # Remove release containers and volumes
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

### Environment Variables

Copy and configure the environment file:
```bash
./ops/scripts/init_env_files postgres
```

Key variables in `.env`:
- `IQ_IMAGE` / `IQ_IMAGE_TAG`: Docker image to use
- `IQ_SITE_NAME`: Frappe site name
- `NGINX_PORT`: Port for web access (default: 8000)
- `DB_HOST` / `DB_PORT`: Database connection

---

## Keeping Updated

### Template Source Storage

After running `copier copy`, the template source is automatically stored in `.copier-answers.yml`:

```yaml
# Auto-generated - DO NOT EDIT MANUALLY
_src_path: gh:iq-company/devcontainerize  # or local path or own fork
_commit: abc123...
app_name: my_app
feature_image_creation: true
# ... all other settings
```

This means subsequent updates only require:
```bash
copier update --trust
```

### Update Commands

```bash
# Preview changes (dry-run)
copier update --trust --pretend

# Show diff
copier update --trust --diff

# Apply updates
copier update --trust

# Force update (overwrite local changes)
copier update --trust --force
```

### Automatic Post-Update Tasks

When `feature_image_creation` is enabled, copier automatically:
1. **Patches `pyproject.toml`**: Adds `baker-cli` to dev dependencies
2. **Installs dependencies**: Runs `pip install -e ".[dev]"`

This ensures `baker-cli` is always available for building Docker images.

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
baker plan                     # Show build plan
baker build --targets dev      # Build dev image
```


## Project Structure

```
your_app/
├── .devcontainer/              # VSCode devcontainer config
│   ├── devcontainer.json
│   ├── compose.dev.override.yml
│   └── honcho/
│       ├── Procfile
│       ├── Procfile_skip_web
│       └── Procfile_skip_worker
├── delivery/
│   ├── container-version       # Semantic version
│   └── resources/
│       ├── container-reduce.sh
│       ├── docker-patches.sh
│       ├── frappe-patches.sh
│       ├── setup_bench_apps.py
│       ├── gunicorn/
│       └── nginx/
├── ops/
│   ├── compose/               # Docker Compose files
│   ├── env/                   # Environment templates
│   └── scripts/               # Helper scripts
├── {{ app_name }}/
│   └── commands/
│       ├── __init__.py
│       └── dist_commands.py
├── Dockerfile.base
├── Dockerfile.builder
├── Dockerfile.dev
├── Dockerfile.release
├── build-settings.yml         # baker-cli configuration
└── Makefile                   # Utility targets (test, version, release)
```

---

## License

MIT License - See LICENSE file for details.
