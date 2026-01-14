#!/bin/bash
set -e

INSTALL_DIR="$HOME/.causeway"
REPO="https://github.com/yourusername/causeway"  # TODO: update with real repo

echo "Installing causeway..."

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull --quiet
else
    echo "Cloning causeway..."
    git clone --quiet "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Install dependencies
echo "Installing dependencies..."
uv sync --quiet

# Init database
uv run python -c "from db import init_db; init_db()"

# Create symlink
echo "Creating symlink..."
mkdir -p "$HOME/.local/bin"
ln -sf "$INSTALL_DIR/causeway" "$HOME/.local/bin/causeway"
chmod +x "$INSTALL_DIR/causeway"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "Add to your shell config:"
    echo '  export PATH="$HOME/.local/bin:$PATH"'
    echo ""
fi

echo ""
echo "Done! Now run:"
echo "  cd your-project"
echo "  causeway connect"
echo ""
