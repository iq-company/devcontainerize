#!/bin/bash
# Install the standalone ops CLI into the active virtual environment.
#
# Installs Python dependencies (click, pyyaml) and creates a wrapper script
# in the venv's bin/ directory so that `ops` is available on PATH.
#
# Usage:
#   source env/bin/activate
#   bash ops/scripts/install_ops.sh          # base deps only
#   bash ops/scripts/install_ops.sh --build  # include baker-cli for image builds
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPS_PY="$SCRIPT_DIR/ops.py"

if [ ! -f "$OPS_PY" ]; then
    echo "Error: ops.py not found at $OPS_PY" >&2
    exit 1
fi

if [ -z "${VIRTUAL_ENV:-}" ]; then
    echo "Error: No active virtual environment. Run 'source env/bin/activate' first." >&2
    exit 1
fi

VENV_BIN="$VIRTUAL_ENV/bin"

# Install Python dependencies
DEPS="click pyyaml"
if [[ "${1:-}" == "--build" ]]; then
    DEPS="$DEPS baker-cli"
fi
echo "📦 Installing dependencies: $DEPS"
pip install --quiet $DEPS

# Create wrapper script
WRAPPER="$VENV_BIN/ops"
cat > "$WRAPPER" << WRAPPER_EOF
#!/bin/bash
exec "$VENV_BIN/python" "$OPS_PY" "\$@"
WRAPPER_EOF
chmod +x "$WRAPPER"

echo "✅ ops CLI installed → $(which ops)"
echo "   Run 'ops --help' to get started."
