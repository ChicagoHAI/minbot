#!/usr/bin/env bash
set -euo pipefail

REPO_URL="git@github.com:ChicagoHAI/minbot.git"
INSTALL_DIR="minbot"

echo "minbot installer"
echo ""

# Install uv
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "uv: found"
fi

# Install gh CLI
if ! command -v gh &>/dev/null; then
    echo "Installing gh CLI..."
    if [[ "$(uname)" == "Darwin" ]]; then
        brew install gh
    else
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
            | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
            | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
        sudo apt-get update && sudo apt-get install -y gh
    fi
else
    echo "gh: found"
fi

# Install Node.js (needed for claude CLI)
if ! command -v node &>/dev/null; then
    echo "Installing Node.js..."
    if [[ "$(uname)" == "Darwin" ]]; then
        brew install node
    else
        curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
        sudo apt-get install -y nodejs
    fi
else
    echo "node: found"
fi

# Install Claude Code CLI
if ! command -v claude &>/dev/null; then
    echo "Installing Claude Code CLI..."
    npm install -g @anthropic-ai/claude-code
else
    echo "claude: found"
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
