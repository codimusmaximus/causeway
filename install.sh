#!/bin/bash
set -e

INSTALL_DIR="$HOME/.causeway"
REPO="https://github.com/codimusmaximus/causeway.git"

echo "Installing causeway..."

# Always use uv - it handles platform detection correctly for native packages like sqlite-vec
# (pip has issues installing the correct architecture on some systems)
if command -v uv &> /dev/null; then
    echo "Found uv"
else
    echo "Installing uv (recommended package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating..."
    cd "$INSTALL_DIR"
    git fetch --quiet
    git reset --hard origin/main --quiet
else
    echo "Downloading..."
    git clone --quiet "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Install dependencies
echo "Installing dependencies..."

uv sync --quiet 2>/dev/null || uv sync

# Create wrapper script for uv
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/causeway" << 'WRAPPER'
#!/bin/bash
CAUSEWAY_CWD="$(pwd)" exec uv run --directory "$HOME/.causeway" causeway "$@"
WRAPPER

chmod +x "$HOME/.local/bin/causeway"

# Ask about call-home telemetry
echo ""
echo "Help improve Causeway by sending anonymous usage data"
echo "(install ID, version, platform - no personal data)"
echo ""
read -p "Enable anonymous usage telemetry? [Y/n] " CALL_HOME_ANSWER
CALL_HOME_ANSWER=${CALL_HOME_ANSWER:-Y}

# Create initial .env with call-home setting
ENV_FILE="$INSTALL_DIR/causeway/.env"
if [ ! -f "$ENV_FILE" ]; then
    if [[ "$CALL_HOME_ANSWER" =~ ^[Nn] ]]; then
        echo "CAUSEWAY_CALL_HOME=false" > "$ENV_FILE"
        echo "Telemetry disabled."
    else
        echo "CAUSEWAY_CALL_HOME=true" > "$ENV_FILE"
        echo "Telemetry enabled."
    fi
else
    # Update existing .env if CAUSEWAY_CALL_HOME is not set
    if ! grep -q "^CAUSEWAY_CALL_HOME=" "$ENV_FILE" 2>/dev/null; then
        if [[ "$CALL_HOME_ANSWER" =~ ^[Nn] ]]; then
            echo "CAUSEWAY_CALL_HOME=false" >> "$ENV_FILE"
            echo "Telemetry disabled."
        else
            echo "CAUSEWAY_CALL_HOME=true" >> "$ENV_FILE"
            echo "Telemetry enabled."
        fi
    fi
fi

# Add to PATH if needed
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc" 2>/dev/null || true
    export PATH="$HOME/.local/bin:$PATH"
fi

# Initial ping (version check + telemetry) - curl only, no deps
bash "$INSTALL_DIR/causeway/hooks/ping.sh" --silent 2>/dev/null &

echo ""
echo "Done! Run: causeway connect"
echo ""
