#!/bin/bash
set -e

CONTAINER_NAME="claude-causeway-sandbox"
IMAGE_NAME="claude-causeway-sandbox"
UI_PORT="${CAUSEWAY_PORT:-8080}"

# Stop and remove existing container if it exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping and removing existing container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if we're in the devcontainer folder or project root
if [[ "$SCRIPT_DIR" == *"devcontainer"* ]]; then
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
    PROJECT_ROOT="$SCRIPT_DIR"
    SCRIPT_DIR="$PROJECT_ROOT/devcontainer"
fi

# Build the image
echo "Building image..."
docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"

# Run the container
echo "Starting container..."
echo "Causeway UI will be available at http://localhost:$UI_PORT"
docker run -it --name "$CONTAINER_NAME" \
    --cap-add=NET_ADMIN \
    --cap-add=NET_RAW \
    -p "$UI_PORT:8000" \
    -v "$PROJECT_ROOT:/workspace" \
    -v claude-code-config:/home/node/.claude \
    -v claude-code-history:/commandhistory \
    -v causeway-data:/home/node/.causeway \
    -w /workspace \
    "$IMAGE_NAME" bash -c '
echo "=========================================="
echo "Claude Code + Causeway DevContainer"
echo "=========================================="
echo ""
echo "Run these commands to get started:"
echo ""
echo "  sudo /usr/local/bin/init-firewall.sh"
echo "  causeway connect"
echo "  claude --dangerously-skip-permissions"
echo ""
echo "To start Causeway UI: causeway ui"
echo "=========================================="
echo ""
exec bash
'
