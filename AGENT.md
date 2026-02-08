# Agent Instructions for devcontainerize_template

This document explains the project architecture, relationships, and non-obvious patterns for AI agents working on this codebase.

## Project Overview

**devcontainerize** is a [Copier](https://copier.readthedocs.io/) template that adds Docker-based development container support to Frappe apps. It generates:
- Docker images (base, builder, dev, release)
- Docker Compose configurations
- VSCode devcontainer setup
- CLI commands (`bench ops ...`)
- Build hooks and scripts

## Key Relationships

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COPIER TEMPLATE SYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  devcontainerize_template/          ──copier copy──►  apps/{app_name}/     │
│  ├── *.jinja files                                    ├── generated files   │
│  └── ops/build/docker-templates/                      └── ops/build/docker/ │
│           ├── {target}/Dockerfile.j2.jinja  ───────►      (Dockerfile.j2)  │
│           └── recipes/00-frappe.yml.jinja   ───────►      (00-frappe.yml)  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BAKER-CLI DOCKERFILE GEN                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ops/build/docker-templates/                                                │
│  ├── {target}/Dockerfile.j2    ──baker gen-docker──►  docker/Dockerfile.*  │
│  ├── recipes/00-frappe.yml                                                  │
│  └── recipes/99-custom.yml                                                  │
│                         ▲                                                   │
│                         │                                                   │
│  baker-cli (built-in)───┘                                                   │
│  └── templates/recipes/                                                     │
│      ├── 00-base.yml        (generic: create_user, install_nvm, ...)       │
│      └── 10-build.yml       (generic: compile_postgres, ...)               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Template Processing Pipeline

### Two-Stage Jinja2 Processing

Files with `.jinja` extension are processed by **Copier** during `copier copy/update`.
Files with `.j2` extension are processed by **baker-cli** during `bench ops dockerfile create/update`.

```
Stage 1 (Copier):     Dockerfile.j2.jinja  →  Dockerfile.j2
Stage 2 (baker-cli):  Dockerfile.j2        →  Dockerfile.{target}
```

**Important**: In `.j2.jinja` files:
- `{{ variable }}` is processed by Copier
- `{% raw %}...{% endraw %}` blocks protect baker-cli Jinja2 from Copier
- Inside `{% raw %}`: `{{ defaults.image_prefix }}` is processed by baker-cli

### Recipe Resolution Order

```
1. baker-cli/templates/recipes/00-base.yml     (built-in generic)
2. baker-cli/templates/recipes/10-build.yml    (built-in build tools)
3. project/recipes/00-frappe.yml               (Frappe-specific, updated by copier)
4. project/recipes/99-custom.yml               (user customizations, never overwritten)
```

Later files override earlier ones by recipe name.

## baker-cli Integration

**baker-cli** is a separate Python package (pip baker-cli) that provides:

1. **Dockerfile Generation** (`baker gen-docker`):
   - Renders `.j2` templates using recipes
   - Supports variants (debian, alpine)
   - Called via `bench ops dockerfile create/update`

2. **Docker Build Orchestration** (`baker build`):
   - Reads `build-settings.yml`
   - Generates HCL for `docker buildx bake`
   - Manages dependency checksums for automatic rebuilds
   - Called via `bench ops build`

### Recipe System

Recipes are reusable Dockerfile snippets with variant support:

```yaml
recipes:
  install_frappe_deps:
    debian: |
      apt-get update && apt-get install -y git vim ...
    alpine: |
      apk add --no-cache git vim ...
    _default: |
      # Used if no variant-specific version exists
```

In templates, use:
- `{{ recipe("name") }}` → outputs `RUN <commands>`
- `{{ recipe_raw("name") }}` → outputs raw commands (for combining in one `RUN`)

## Build Targets and Dependencies

```
base     →  builder  →  dev
                    ↘→  release
```

- **base**: Python, Node.js, system packages (no Frappe)
- **builder**: Compiled binaries (nginx, psql) - used as build cache
- **dev**: Full development environment with Frappe + apps
- **release**: Minimal production image (cleaned from dev)

## Variant System (Debian vs Alpine)

Each target supports multiple base OS variants:

```
docker-templates/{target}/
├── Dockerfile.j2           # Main template
└── variants/
    ├── debian.yml          # Debian-specific defaults
    └── alpine.yml          # Alpine-specific defaults
```

Use in templates:
```jinja2
{% if base_variant == "debian" %}
  {{ recipe("compile_postgres") }}
{% else %}
  # Alpine: use apk packages instead
{% endif %}
```

**Critical Alpine Differences**:
- No glibc → NVM installs don't work, use `apk add nodejs npm`
- Nginx installed via `apk`, not compiled to `/opt/nginx/`
- Paths differ: `/var/lib/nginx/` instead of `/opt/nginx/`
- Needs `coreutils` for GNU tools compatibility

## Environment Files System

```
ops/env/
├── .env              # Shared defaults (IMAGE, COMPOSE_PROFILES)
├── .env.dev          # Dev stage (HOST_UID, VSCODE_SETTINGS_PATH)
├── .env.staging      # (example) Staging-specific
└── .env.prod         # (example) Production-specific

ops/env-templates/
├── env.template.jinja           # Base template
├── env.shared.template.jinja    # Shared env template
└── env.*.addon.template.jinja   # DBMS-specific additions
```

**Loading Order**: `.env` (shared) + `.env.{stage}` (stage-specific)

## Build Hooks

See `ops/build/BUILD_HOOKS.md` for complete documentation.

Key hook files:
- `frappe-patches.sh` - Before `bench init`
- `app-patches.sh` - After app installation
- `{app_name}-patches.sh` - Before `pip install` (reduce dependencies!)
- `ops_release_cleanup` (in ops_hooks.py) - Release image cleanup

## Non-Obvious Patterns

### 1. copier-answers.yml Location

After `copier copy`, answers are moved to `ops/.copier-answers.yml` (not root).
This is handled by `ops/copier/move_copier_answers.py`.

### 2. _skip_if_exists Files

Files listed in `copier.yaml:_skip_if_exists` are only created on initial copy,
never overwritten on update. Important for user customizations:
- `ops/build/stages.yml`
- `ops/build/docker-templates/recipes/99-custom.yml`
- `pyproject.toml`

### 3. Docker Compose Path Resolution

In devcontainer overrides, paths are relative to the **project directory**
(set by the first `-f` file), NOT the override file location.

```yaml
# .devcontainer/compose.dev.override.yml
# This is WRONG (relative to override file):
#   ../ops/scripts/runtime/init_site.sh
# This is CORRECT (relative to ops/compose/):
#   ../scripts/runtime/init_site.sh
```

### 4. YAML Interpolation vs Container Environment

Docker Compose resolves `${VAR}` in the YAML **before** reading `env_file:`.
Variables needed for `image:` directives must be in:
- Shell environment before `docker compose up`
- A `.env` file in the compose project directory

### 5. DDL Mode (PostgreSQL)

When `DB_USER=""` (empty), the system uses DDL mode where:
- `DB_SUPER_USER` owns all objects
- `DB_NAME` is used as the site's database name
- No separate application user is created

### 6. Build Cache Layers

Cache cleanup MUST happen in the same `RUN` command as installations:

```dockerfile
# WRONG (cleanup in separate layer doesn't reduce size):
RUN pip install ...
RUN rm -rf ~/.cache/pip

# CORRECT:
RUN pip install ... && rm -rf ~/.cache/pip
```

## Common Tasks

### Add a new recipe

1. Add to `ops/build/docker-templates/recipes/99-custom.yml` (never overwritten)
2. Use in template: `{{ recipe("my_recipe") }}`

### Support a new OS variant

1. Create `ops/build/docker-templates/{target}/variants/{variant}.yml`
2. Add variant-specific recipe implementations in `99-custom.yml`
3. Generate: `bench ops dockerfile create --variant {variant}`

### Update baker-cli

baker-cli is installed in the project's venv. After changes:
```bash
cd /path/to/baker-cli
pip install -e .
```

### Debug Dockerfile generation

```bash
bench ops dockerfile update --dry-run --diff
```

## File Naming Conventions

| Pattern | Processed By | Example |
|---------|--------------|---------|
| `*.jinja` | Copier | `ops_commands.py.jinja` → `ops_commands.py` |
| `*.j2.jinja` | Copier, then baker-cli | `Dockerfile.j2.jinja` → `Dockerfile.j2` → `Dockerfile.dev` |
| `*.j2` | baker-cli only | `Dockerfile.j2` → `Dockerfile.dev` |

## Related Projects

- **baker-cli**: `pip baker-cli` - Docker build orchestration
- **frappe-bench**: Frappe's CLI tool, extended via `bench ops` commands
- **copier**: Template engine (external package)
