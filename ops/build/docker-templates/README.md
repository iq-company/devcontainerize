# Dockerfile Templates

This directory contains Jinja2 templates for generating Dockerfiles.

## Workflow

```
docker-templates/{target}/Dockerfile.j2  →  bench ops dockerfile-gen  →  docker/Dockerfile.{target}
                                                    ↑
                              recipes/00-frappe.yml + variants/debian.yml
```

## Directory Structure

```
docker-templates/
├── recipes/                  # Project-specific recipes
│   ├── 00-frappe.yml         # Frappe recipes (updated by copier)
│   └── 99-custom.yml         # ← YOUR recipes (never overwritten)
├── base/
│   ├── Dockerfile.j2         # Template for base image
│   └── variants/
│       ├── debian.yml        # Debian-specific config
│       └── alpine.yml        # Alpine-specific config
├── builder/
│   └── Dockerfile.j2
├── dev/
│   └── Dockerfile.j2
└── release/
    └── Dockerfile.j2

docker/                       # ← GENERATED, do not edit!
├── Dockerfile.base
├── Dockerfile.builder
├── Dockerfile.dev
└── Dockerfile.release
```

## Commands

```bash
# Show status and available variants
bench ops dockerfile

# Create Dockerfiles from templates
bench ops dockerfile create               # Create all (debian)
bench ops dockerfile create -v alpine     # Create for Alpine

# Regenerate after template/recipe changes
bench ops dockerfile update               # Update all
bench ops dockerfile update -t dev        # Update specific target

# Preview without writing
bench ops dockerfile create --dry-run --diff
```

## Convention over Configuration

Both paths are derived from the target name:

| Property | Convention | Example (target: `dev`) |
|----------|------------|-------------------------|
| `dockerfile_template` | `docker-templates/{target}/Dockerfile.j2` | `docker-templates/dev/Dockerfile.j2` |
| `dockerfile` | `docker/Dockerfile.{target}` | `docker/Dockerfile.dev` |

Only specify these in `build-settings.yml` to **override** the convention.

## Recipe Hierarchy

```
baker-cli (built-in)           ← Base recipes (install_packages, cleanup_apt, etc.)
      ↓ overridden by
recipes/00-frappe.yml          ← Frappe-specific (updated by copier update)
      ↓ overridden by
recipes/99-custom.yml          ← YOUR customizations (never overwritten)
```

**baker-cli** provides generic recipes. The **project** only extends/overrides what's needed.

## Customizing Recipes

### Your recipes in `99-custom.yml`

This file is **never** overwritten by `copier update`:

```yaml
# recipes/99-custom.yml
recipes:
  # Add a new recipe
  install_my_tool:
    debian: |
      RUN apt-get update && apt-get install -y my-tool
    alpine: |
      RUN apk add --no-cache my-tool

  # Override an existing recipe (from baker-cli or 00-frappe.yml)
  install_base_packages_raw:
    debian: |
      apt-get update && apt-get install -y \
          curl wget git vim htop  # Custom package list
```

### Additional recipe files

You can also add your own files (e.g., `50-myproject.yml`):

```yaml
# recipes/50-myproject.yml
recipes:
  install_project_deps:
    _default: |
      pip install my-special-package
```

### Where are the base recipes?

Generic recipes (like `install_packages`, `cleanup_apt_raw`) are **built into baker-cli**
and don't need to be in the project. The project only contains:

1. `00-frappe.yml` - Frappe-specific recipes (updated by `copier update`)
2. `99-custom.yml` - Your own customizations (never overwritten)

## Defaults

Defaults are defined in `build-settings.yml` under `dockerfile_defaults:`:

```yaml
dockerfile_defaults:
  python_version: "3.12"
  debian_base: "bookworm"
  pg_version: "16.4"
  nginx_version: "1.27.4"
```

Override via CLI: `bench ops dockerfile-gen --set python_version=3.11`
