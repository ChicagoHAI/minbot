#!/usr/bin/env bash
set -euo pipefail

REPO_URL="git@github.com:ChicagoHAI/minbot.git"
INSTALL_DIR="minbot"

echo "minbot installer"
echo ""

missing=()

# Install uv (user-local, no sudo needed)
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "uv: found"
fi

# Check gh CLI
if ! command -v gh &>/dev/null; then
    missing+=("gh (https://cli.github.com)")
else
    echo "gh: found"
fi

# Install Claude Code CLI
if ! command -v claude &>/dev/null; then
    echo "Installing Claude Code CLI..."
    curl -fsSL https://claude.ai/install.sh | bash
else
    echo "claude: found"
fi

if [[ ${#missing[@]} -gt 0 ]]; then
    echo ""
    echo "Missing dependencies (install these first):"
    for dep in "${missing[@]}"; do
        echo "  - $dep"
    done
    exit 1
fi

# Clone repo if not already inside it
if [[ ! -f "pyproject.toml" ]] || ! grep -q 'name = "minbot"' pyproject.toml 2>/dev/null; then
    echo ""
    echo "Cloning minbot..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
uv sync

echo ""
echo "Done! Next steps:"
echo "  cd ${INSTALL_DIR}"
echo "  uv run python -m minbot setup      # configure tokens and repos"
echo "  uv run minbot                      # start the bot"
