# Build Hooks & Cleanup Tasks

This document explains how to customize the Docker build process and add cleanup tasks.

## Build Hook Timing

During `setup_bench_apps.py` execution, several hook points are available:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DOCKER BUILD PHASE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. frappe-patches.sh        (before bench init)                    │
│     └─ Modify Frappe source before initialization                   │
│                                                                     │
│  2. bench init               (creates bench structure)              │
│                                                                     │
│  3. App installation         (apps moved to bench/apps/)            │
│                                                                     │
│  4. app-patches.sh           (after app installation)               │
│     └─ Modify installed apps, apply general patches                 │
│                                                                     │
│  5. {app_name}-patches.sh    (before pip install) ◄─ IMPORTANT      │
│     └─ Modify pyproject.toml to remove optional packages            │
│     └─ This is where you reduce image size!                         │
│                                                                     │
│  6. bench setup requirements (pip install, yarn install)            │
│                                                                     │
│  7. bench build              (frontend assets)                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     RELEASE IMAGE BUILD PHASE                       │
│                  (only for Dockerfile.release*)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  CLEANER STAGE (FROM dev):                                          │
│  8. ops_release_cleanup hooks (via call_root_*_release_dist.py)     │
│     └─ release-cleaner.sh app   (build tools, node_modules, .git)   │
│     └─ release-cleaner-custom.sh app  (project-specific)            │
│                                                                     │
│  FINAL STAGE (FROM base):                                           │
│  9. pip install frappe-bench    (reinstall bench CLI)                │
│  10. release-cleaner.sh system  (git imports, pip/setuptools)        │
│      └─ release-cleaner-custom.sh system  (project-specific)        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Creating Build Hooks

### 1. frappe-patches.sh

Location: `ops/build/resources/frappe-patches.sh`

Called **before** `bench init`. Use this to patch Frappe source code.

```bash
#!/usr/bin/bash
set -e
# Example: Patch Frappe files before bench initialization
# sed -i 's/old/new/' /path/to/frappe/file.py
```

### 2. app-patches.sh

Location: `ops/build/resources/app-patches.sh`

Called **after** apps are installed but **before** requirements are installed.

```bash
#!/usr/bin/bash
set -e
# Example: Apply patches to installed apps
# This runs from home_dir (e.g., /home/iqa)
```

### 3. {app_name}-patches.sh (Project-Specific)

Location: `ops/build/resources/{your_app_name}-patches.sh`

Called **before** `bench setup requirements`. This is the key hook for reducing image size by removing optional packages from `pyproject.toml`.

**This file is NOT part of the template** - create it in your project if needed.

Example structure:
```bash
#!/usr/bin/bash
set -e

# Define which packages to remove based on ENABLE_* environment variables
# If ENABLE_TRANSFORMERS is not "true", remove transformers packages

if [ "$ENABLE_TRANSFORMERS" != "true" ]; then
    # Remove transformers from pyproject.toml
    sed -i '/transformers/d' apps/myapp/pyproject.toml
fi
```

## Image Cleaner Scripts

Each target has a **main cleaner** (template-managed, updated by copier) and an optional **custom cleaner** (project-specific, never overwritten by copier):

| Target | Main Cleaner | Custom Cleaner |
|--------|-------------|----------------|
| dev | `dev-cleaner.sh` | `dev-cleaner-custom.sh` |
| release | `release-cleaner.sh` | `release-cleaner-custom.sh` |

Both support two modes:

| Mode | Purpose |
|------|---------|
| `app` | Remove build artifacts, dev node_modules, venv packages, caches |
| `system` | Remove system-level Python packages, patch bench modules |

The main cleaner handles **universal** cleanups (applies to every Frappe project).
The custom cleaner handles **project-specific** cleanups (e.g., removing specific packages your project doesn't need).

### Adding Project-Specific Cleanups

Edit `release-cleaner-custom.sh` or `dev-cleaner-custom.sh`:

```bash
cleanup_app_custom() {
    # Remove packages your project doesn't need
    rm -rf "${BENCH_PATH}/apps/frappe/node_modules/@sentry"
    $VENV_PIP uninstall -y jedi parso 2>/dev/null || true
}

case "${MODE}" in
    app)    cleanup_app_custom ;;
    system) ;;
    all)    cleanup_app_custom ;;
esac
```

## Release Cleanup Hooks (ops_release_cleanup)

The `ops_release_cleanup` hook in `ops_hooks.py` triggers the release cleaner during the **Cleaner stage**:

```python
# In your app's ops_hooks.py
ops_release_cleanup = [
    # release-cleaner.sh runs in 'app' mode by default
    # Project-specific cleanups are in release-cleaner-custom.sh (called automatically)
    {"script": "../ops/build/resources/release-cleaner.sh"},
]
```

The **system mode** is called separately in the Final stage of `Dockerfile.release`, after `pip install frappe-bench`.

Additional hook types are supported:

```python
ops_release_cleanup = [
    {"script": "../ops/build/resources/release-cleaner.sh"},    # Run a script
    {"bash": "rm -rf /some/path"},                               # Run a bash command
    {"function": "myapp.utils.cleanup.remove_dev_files"},        # Run a Python function
    {"bash": "...", "context": "only_during_build"},             # Only during Docker build
]
```

### Context Options

| Context | Description |
|---------|-------------|
| (none) | Runs always (during build and when called manually) |
| `only_during_build` | Only runs during Docker image build |

### How it works

1. `Dockerfile.release` Cleaner stage calls `call_root_*_release_dist.py`
2. This script reads `ops_release_cleanup` hooks from all installed apps
3. Hooks are executed in order → `release-cleaner.sh app` → `release-cleaner-custom.sh app`
4. Runs as **root** to allow deleting system files
5. In the Final stage, `release-cleaner.sh system` runs after `pip install frappe-bench`

## Environment Variables for Conditional Builds

Pass environment variables via `build-settings.yml` to conditionally include/exclude features:

```yaml
# In build-settings.yml
targets:
  dev:
    build_args:
      ENABLE_TRANSFORMERS: "true"
      ENABLE_OCR: "false"
      ENABLE_NLP: "false"
```

Your `{app_name}-patches.sh` can then check these variables to modify `pyproject.toml`.

## Best Practices

1. **Reduce in the same layer**: Cache cleanup should happen in the same `RUN` command as the installation to avoid layer bloat.

2. **Use {app_name}-patches.sh for pip packages**: Remove optional packages BEFORE `bench setup requirements` runs.

3. **Use ops_release_cleanup for file cleanup**: Delete unnecessary files, caches, and dev tools in release images.

4. **Test locally first**: Run cleanup scripts manually before adding them to the build process.

5. **Document your hooks**: Add comments explaining what each hook does and why.

## Example: Reducing Image Size

### Step 1: Create {app_name}-patches.sh

```bash
#!/usr/bin/bash
# myapp-patches.sh - Remove optional packages before pip install

set -e

PYPROJECT="apps/myapp/pyproject.toml"

# Remove heavy ML packages if not needed
if [ "$ENABLE_ML" != "true" ]; then
    sed -i '/transformers/d' "$PYPROJECT"
    sed -i '/torch/d' "$PYPROJECT"
    sed -i '/tensorflow/d' "$PYPROJECT"
fi
```

### Step 2: Add release cleanup in release-cleaner-custom.sh

```bash
# release-cleaner-custom.sh
cleanup_app_custom() {
    # Remove dev-only venv packages
    $VENV_PIP uninstall -y jedi parso IPython 2>/dev/null || true

    # Remove heavy test frameworks
    rm -rf "${BENCH_PATH}/apps/myapp/node_modules/jest"*

    # Remove disabled features
    rm -rf "${BENCH_PATH}/apps/myapp/delivery"
}

case "${MODE}" in
    app)    cleanup_app_custom ;;
    system) ;;
    all)    cleanup_app_custom ;;
esac
```

### Step 3: Dev image cleanup in dev-cleaner-custom.sh

```bash
# dev-cleaner-custom.sh
cleanup_app_custom() {
    # Remove packages not needed even during development
    "${BENCH_PATH}/env/bin/pip" uninstall -y jedi parso 2>/dev/null || true
    rm -rf "${BENCH_PATH}/apps/frappe/cypress"
}

case "${MODE}" in
    app)    cleanup_app_custom ;;
    system) ;;
    all)    cleanup_app_custom ;;
esac
```

> **Note**: Build caches (yarn, uv, pip) are automatically cleaned by the main `dev-cleaner.sh` and `release-cleaner.sh` — no need to add these to your custom cleaners.
