#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="${1:?Usage: init_project.sh <project-name> [template-path]}"
TEMPLATE_PATH="${2:-$(cd "$(dirname "$0")/.." && pwd)}"
PROJECTS_ROOT="$(dirname "$TEMPLATE_PATH")"
DEST="$PROJECTS_ROOT/$PROJECT_NAME"

if [ -d "$DEST" ]; then
    echo "ERROR: Destination '$DEST' already exists."
    exit 1
fi

echo "[1/5] Creating project from template..."
mkdir -p "$DEST"
cp -r "$TEMPLATE_PATH/"* "$DEST/" 2>/dev/null || true
cp -r "$TEMPLATE_PATH"/.* "$DEST/" 2>/dev/null || true
cd "$DEST"

if [ ! -f "AGENT_SYSTEM.md" ]; then
  echo "ERROR: AGENT_SYSTEM.md missing from scaffold. This file is mandatory."
  exit 1
fi

echo "[2/5] Initializing Python environment (uv)..."
uv venv
uv sync

echo "[3/5] Initializing project harness..."
uv run python src/core/harness.py || true

echo "[4/5] Initializing git repository..."
git init
git add .
git commit -m "Initial commit: scaffold from LTADE template"

echo "[5/5] Setup complete!"
echo ""
echo "Location: $DEST"
echo ""
echo "Next steps:"
echo "  1. cd $DEST"
echo "  2. source .venv/bin/activate"
echo "  3. opencode ."
echo "  4. Update spec/design.md with your architecture plan"
echo "  5. Edit .env with your API keys"
