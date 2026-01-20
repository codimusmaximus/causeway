#!/bin/bash
set -e

INSTALL_DIR="$HOME/.causeway"
REPO="https://github.com/codimusmaximus/causeway.git"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}Installing causeway...${NC}"

# Always use uv - it handles platform detection correctly for native packages like sqlite-vec
# (pip has issues installing the correct architecture on some systems)
if command -v uv &> /dev/null; then
    echo -e "${DIM}Found uv${NC}"
else
    echo -e "${DIM}Installing uv (recommended package manager)...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${DIM}Updating...${NC}"
    cd "$INSTALL_DIR"
    git fetch --quiet
    git reset --hard origin/main --quiet
else
    echo -e "${DIM}Downloading...${NC}"
    git clone --quiet "$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Install dependencies
echo -e "${DIM}Installing dependencies...${NC}"
uv sync --quiet 2>/dev/null || uv sync

# Create wrapper script for uv
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/causeway" << 'WRAPPER'
#!/bin/bash
CAUSEWAY_CWD="$(pwd)" exec uv run --directory "$HOME/.causeway" causeway "$@"
WRAPPER
chmod +x "$HOME/.local/bin/causeway"

# Add to PATH if needed
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc" 2>/dev/null || true
    export PATH="$HOME/.local/bin:$PATH"
fi

echo ""
echo -e "  ${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "  ${GREEN}║                                       ║${NC}"
echo -e "  ${GREEN}║       ${BOLD}Causeway installed!${NC}${GREEN}             ║${NC}"
echo -e "  ${GREEN}║                                       ║${NC}"
echo -e "  ${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "  Run ${CYAN}causeway setup${NC} to configure your environment"
echo ""
