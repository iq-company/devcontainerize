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
- [Optional Services (Compose Profiles)](#optional-services-compose-profiles)
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
│   │   ├── stages.yml             # Stage configuration (dev, staging, prod)
│   │   ├── .copier-answers.yml    # Copier answers
│   │   └── VERSION                # Semantic version
│   ├── compose/                   # Docker Compose files
│   │   ├── compose.base.yml
│   │   ├── compose.postgres.yml
│   │   ├── compose.mariadb.yml
│   │   └── compose.release.yml
│   ├── env/                       # Generated .env files (gitignored)
│   │   ├── .env                   # ⚠️ Shared defaults
│   │   ├── .env.dev               # ⚠️ Dev stage (for vscode devcontainer setup)
│   │   ├── .env.staging           # ⚠️ Staging stage
│   │   └── .env.prod              # ⚠️ Prod stage
│   ├── env-templates/             # Environment templates
│   │   ├── env.shared.template    # → .env (shared defaults)
│   │   ├── env.template           # → .env.STAGE (stage-specific)
│   │   ├── env.dev.addon.template # → appended to .env.dev only
│   │   └── env.*.addon.template   # DBMS-specific additions
│   ├── scripts/
│   │   ├── common/                # Shared utilities
│   │   │   └── load_env.sh        # Load .env + .env.STAGE cascade
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
│   │   └── release/               # Host-side release scripts
│   │       ├── run_release_helper.sh
│   │       ├── stop_release_helper.sh
│   │       └── clean_release_helper.sh
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

The `bench ops` CLI provides commands for template updates, builds, stages, and maintenance.

```bash
# Template Update
bench ops update                # Update from template
bench ops update -d/--dry       # Preview changes (dry run)
bench ops update -r/--recopy    # Recopy template (for dirty repos)

# Version Management
bench ops version               # Show current version
bench ops version -b/--bump     # Bump bugfix version (default)
bench ops version -b -m/--major # Bump major version
bench ops version -b -f/--feature # Bump feature version
bench ops version -b -c/--commit  # Bump and commit

# Build (wrapper for baker-cli)
bench ops build                 # Show build plan (default)
bench ops build -i/--images     # Build Docker images
bench ops build -i -p/--push    # Build and push to registry
bench ops build -i -f/--force   # Force rebuild

# Stage Management
bench ops stage ls              # List all defined stages
bench ops stage ls -v           # List with details
bench ops stage show <name>     # Show stage configuration
bench ops stage run <name>      # Start environment for stage
bench ops stage stop <name>     # Stop environment for stage
bench ops stage clean <name>    # Clean up stage containers
bench ops stage clean <name> -v # Also remove volumes
bench ops stage build <name>    # Build images for stage
bench ops stage env <name>      # Generate .env file for stage
bench ops stage add <name>      # Add a new stage
bench ops stage rm <name>       # Remove a stage

# Testing
bench ops run-tests             # Run all whitelisted tests (in ops_hooks.py)
bench ops run-tests -s Auth     # Run tests for specific section
```

<details>
<summary>Internal commands (for build scripts)</summary>

```bash
# Called by Dockerfile during release build - not for manual use
bench ops release-dist          # Run cleanup tasks (ops_release_cleanup hooks)
bench ops release-dist -s prod  # Filter by stage
```
</details>

### Build Hooks & Cleanup

For customizing the Docker build process (removing optional packages, cleaning up files), see **[`ops/build/BUILD_HOOKS.md`](ops/build/BUILD_HOOKS.md)**.

Key concepts:
- **`{app_name}-patches.sh`**: Remove optional packages from `pyproject.toml` BEFORE pip install
- **`ops_release_cleanup` hooks**: Clean up files in release images
- **`context: only_during_build`**: Run hooks only during Docker build, not manually

### Stage Configuration

Stages define runtime environments and their relationship to Docker build targets.

#### Build Targets vs Runtime Stages

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ BUILD TARGETS (baker-cli)           │ RUNTIME STAGES                                │
├─────────────────────────────────────┼──────────────────────────────────-────────────┤
│ base       → Image base for all     │                                               │
│ builder    → Compilation tools      │                                               │
│ dev        → Development image      │ dev      → Local development in devcontainers │
│ release    → Production image       │ staging  → Staging environment                │
│ release-alpine → Minimal image      │ prod     → Production                         │
└─────────────────────────────────────┴───────────────────────────────────────────────┘
```

- **Build targets** define *how* images are built (Dockerfiles, layers)
- **Runtime stages** define *what* goes into images (apps, refs) and *where* they run

#### Stage Definition

Stages are defined in `ops/build/stages.yml`:

```yaml
# Base apps - built into standard dev image (order matters)
apps:
  - name: frappe
    source: https://github.com/frappe/frappe
    ref: version-15           # branch, tag, or commit

  - name: my_app
    source: local
    ref: HEAD

stages:
  # Development stage - uses dev target
  dev:
    target: dev               # baker-cli target to use
    env_file: .env.dev        # Stage-specific env (loads after shared .env)
    profiles: [db, redis]
    # image: ghcr.io/org/repo/my_app-dev:latest  # Optional: pull from registry

  # Staging uses same apps as dev → can use standard release image
  staging:
    target: release
    env_file: .env.staging
    profiles: []              # External DB/Redis
    # image: ghcr.io/org/repo/my_app-release:latest  # Pull pre-built image

  # Prod pins specific versions → needs separate image build
  prod:
    extends: staging
    env_file: .env.prod
    image_suffix: -prod       # REQUIRED because of app override: creates my_app-release-prod
    apps:                     # Override app refs
      - name: frappe
        ref: v15.47.0
      - name: my_app
        ref: v1.0.0
```

#### When `image_suffix` is Required

If a stage customizes `apps` (different refs or ignored apps), it needs a **separate image**:

| Scenario | `image_suffix` |
|----------|----------------|
| Same apps as base, same target | Not needed |
| Same apps, different target | Not needed (target determines image) |
| Custom app refs | **Required** |
| Ignored apps | **Required** |

The CLI validates this and shows warnings:
```bash
bench ops stage ls -v    # Shows validation warnings
bench ops stage show prod  # Shows image name and validation
```

#### How Apps Get Into Images

When you run `bench ops stage build <stage>`, the CLI:

1. **Reads the stage's app definitions** from `stages.yml`
2. **Sets environment variables** that the Dockerfile picks up:
   - `FRAPPE_REF` - Git reference for Frappe (branch, tag, or commit)
   - `CUSTOM_APPS` - Comma-separated list of additional apps
   - `PRODUCTION_BUILD` - `true` for release targets (yarn and pips will only install production requirements), `false` otherwise
3. **Calls baker-cli** which runs `docker buildx bake`
4. **Dockerfile.dev** calls `setup_bench_apps.py` with these values

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ stages.yml                                                                   │
│   apps:                                                                      │
│     - name: frappe, ref: v15.47.0                                            │
│     - name: my_app, source: local            # Main app (copied via COPY)    │
│     - name: erpnext, source: https://..., ref: v15                           │
│     - name: other_local, source: local       # Additional local app          │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ bench ops stage build prod                                                   │
│   → FRAPPE_REF=v15.47.0                                                      │
│   → CUSTOM_APPS=https://github.com/frappe/erpnext#v15,/opt/apps/other_local  │
│   → PRODUCTION_BUILD=true                                                    │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Dockerfile.dev                                                               │
│   ARG FRAPPE_REF, CUSTOM_APPS, PRODUCTION_BUILD                              │
│   COPY . /opt/apps/my_app                    # Main app copied here          │
│   RUN setup_bench_apps.py --frappe-ref ... --custom-apps ... [--production]  │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Note:** The main app (`my_app`) is copied into the image via `COPY` in the Dockerfile.
Additional apps are passed via `CUSTOM_APPS`:
- Remote: `https://github.com/org/app#ref`
- Local: `/opt/apps/app_name` (must be available in build context)

The `setup_bench_apps.py` script:
- Clones Frappe at the specified ref
- Installs the main app from `/opt/apps/{{ app_name }}`
- Clones/installs all custom apps (remote or local paths)
- Builds frontend assets (with `--production` for release targets)

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

Environment configuration uses a **shared + stage** pattern:

```
Load Order: .env (shared) → .env.STAGE (overrides)
```

### File Structure

```
ops/env/
├── .env          # Shared defaults (all stages)
├── .env.dev      # Dev stage overrides
├── .env.staging  # Staging stage overrides
└── .env.prod     # Prod stage overrides
```

### Shared vs Stage-Specific

| In `.env` (shared) | In `.env.STAGE` (stage-specific) |
|--------------------|----------------------------------|
| `IQ_IMAGE`, `IQ_IMAGE_TAG` | `COMPOSE_PROJECT_NAME` (unique per stage) |
| `IQ_SITE_NAME`, `IQ_BRAND_NAME` | `DBMS`, `DB_HOST`, `DB_PORT` |
| `REDIS_*`, `SOCKETIO_PORT` | `DB_*` credentials |
| `NGINX_PORT`, `WEBDB_PORT` (defaults) | `IQ_ADMIN_PW` |
| `COMPOSE_PROFILES` (defaults) | `OPENID_*` settings |
| | `HOST_UID`, `HOST_GID` (dev only) |

Stage-specific files can **override** any shared value:
```bash
# .env (shared)
COMPOSE_PROFILES=

# .env.dev (override for dev stage)
COMPOSE_PROFILES=ocr,monitoring
```

### Templates (committed to Git)

| File | Generates | Purpose |
|------|-----------|---------|
| `ops/env-templates/env.shared.template` | `.env` | Shared defaults |
| `ops/env-templates/env.template` | `.env.STAGE` | Stage-specific config |
| `ops/env-templates/env.dev.addon.template` | (appended to `.env.dev`) | Dev-only vars |
| `ops/env-templates/env.*.addon.template` | (appended) | DBMS-specific additions |

### Initialization

```bash
# Create env files for a stage
bench ops stage env dev        # Creates .env + .env.dev
bench ops stage env staging    # Creates .env + .env.staging

# Or directly via script
./ops/scripts/devcontainer/init_env_files postgres           # Default: .env.dev
ENV_FILE_SUFFIX=.staging ./ops/scripts/devcontainer/init_env_files postgres
```

### Loading Environment in Scripts

Use the helper script to load both files:

```bash
# In shell scripts
source ./ops/scripts/common/load_env.sh           # Loads .env + .env.dev
source ./ops/scripts/common/load_env.sh staging   # Loads .env + .env.staging

# Variables are then directly available
echo $COMPOSE_PROJECT_NAME
echo $DBMS
```

### Key Variables

| Variable | Location | Description |
|----------|----------|-------------|
| `IQ_IMAGE` | shared | Docker image name |
| `IQ_IMAGE_TAG` | shared | Docker image tag |
| `IQ_SITE_NAME` | shared | Frappe site name |
| `DBMS` | stage | Database type (postgres, mariadb, sqlite) |
| `DB_HOST` | stage | Database host |
| `DB_PORT` | stage | Database port |
| `DB_ROOT_PASSWORD` | stage | Database root password |
| `DB_SUPER_USER` | stage | Super user for DDL operations |
| `COMPOSE_PROJECT_NAME` | stage | Unique per stage |
| `NGINX_PORT` | shared (override in stage) | Port for web access |
| `COMPOSE_PROFILES` | shared (override in stage) | Active profiles |

---

## Optional Services (Compose Profiles)

Docker Compose profiles allow services to be conditionally started.

### How It Works

1. **Define a service with a profile** in a compose file:
   ```yaml
   # ops/compose/compose.with-ocr-ext.yml
   services:
     ocr-rt:
       profiles: [ocr]  # Only starts when 'ocr' profile is active
       build: ../build/resources/ocr-extensions
   ```

2. **Include the file** in `compose.base.yml`:
   ```yaml
   include:
     - ./compose.with-ocr-ext.yml
     - ./compose.${DBMS:-postgres}.yml
   ```

3. **Activate the profile** via environment:
   ```bash
   # In .env or .env.STAGE
   COMPOSE_PROFILES=ocr

   # Multiple profiles
   COMPOSE_PROFILES=ocr,monitoring,debug
   ```

### Per-Stage Profiles

Different stages can have different profiles:

```bash
# .env (shared) - no profiles by default
COMPOSE_PROFILES=

# .env.dev - dev gets OCR and monitoring
COMPOSE_PROFILES=ocr,monitoring

# .env.prod - prod only gets monitoring
COMPOSE_PROFILES=monitoring
```

### Creating Optional Services

See `ops/compose/compose.with-optional-service.example.yml` for a template:

```yaml
services:
  my-service:
    profiles: [myprofile]
    image: alpine:latest
    # build: ../build/resources/my_service/
```

### Starting with Profiles

```bash
# Via bench ops (reads COMPOSE_PROFILES from .env)
bench ops stage run dev

# Via docker compose directly
docker compose --profile ocr up
```

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
