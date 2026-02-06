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
│  8. ops_release_cleanup hooks (via call_root_iq_release_dist.py)    │
│     └─ Delete unnecessary files, caches, dev dependencies           │
│     └─ Runs as root to delete system files                          │
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

## Release Cleanup Hooks (ops_release_cleanup)

For cleanup tasks that run during **release image builds**, use the `ops_release_cleanup` hook in your app's `ops_hooks.py`:

```python
# In your app's ops_hooks.py

ops_release_cleanup = [
    # Run a bash command
    {"bash": "find /home/iqa/bench -name '*.pyc' -delete"},

    # Run a script (path relative to app directory)
    {"script": "../ops/build/resources/container-reduce.sh"},

    # Run a Python function
    {"function": "myapp.utils.cleanup.remove_dev_files"},

    # Only run during Docker build (not when called manually)
    {"bash": "rm -rf /some/path", "context": "only_during_build"},
]
```

### Context Options

| Context | Description |
|---------|-------------|
| (none) | Runs always (during build and when called manually) |
| `only_during_build` | Only runs during Docker image build (when docker is not available in container) |

### How it works

1. `Dockerfile.release` calls `call_root_iq_release_dist.py`
2. This script reads `ops_release_cleanup` hooks from all installed apps
3. Hooks are executed in order (bash commands, scripts, or functions)
4. Runs as **root** to allow deleting system files

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

### Step 2: Add release cleanup hooks

```python
# ops_hooks.py
ops_release_cleanup = [
    # Remove Python cache
    {"bash": "find /home/iqa/bench -name '*.pyc' -delete"},
    {"bash": "find /home/iqa/bench -name '__pycache__' -type d -delete"},

    # Remove development files
    {"bash": "rm -rf /home/iqa/bench/apps/*/tests"},
    {"bash": "rm -rf /home/iqa/bench/apps/*/.git"},

    # Run container-reduce script
    {"script": "../ops/build/resources/container-reduce.sh"},
]
```

### Step 3: Cleanup build caches in Dockerfile

The template already includes cache cleanup in the same layer as `setup_bench_apps.py`:

```dockerfile
RUN python3 setup_bench_apps.py ... ; \
    rm -rf ~/.cache/yarn ~/.cache/uv ~/.cache/pip /tmp/*
```
