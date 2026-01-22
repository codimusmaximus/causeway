#!/bin/bash
# run_local.sh - Run E2E tests locally using Docker
#
# Usage:
#   ./run_local.sh              # Run all tests
#   ./run_local.sh --build      # Force rebuild of Docker image
#   ./run_local.sh --scenario 01_block_rm_rf  # Run specific scenario
#
# Environment variables:
#   ANTHROPIC_API_KEY - Required for Claude Code
#   OPENAI_API_KEY    - Required for Causeway embeddings
#
# You can also create a .env file in the tests/e2e directory with these keys.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
IMAGE_NAME="causeway-e2e"
LOG_DIR="$SCRIPT_DIR/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
FORCE_BUILD=false
SPECIFIC_SCENARIO=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --build|-b)
            FORCE_BUILD=true
            shift
            ;;
        --scenario|-s)
            SPECIFIC_SCENARIO="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --build, -b              Force rebuild of Docker image"
            echo "  --scenario, -s NAME      Run only the specified scenario"
            echo "  --help, -h               Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  ANTHROPIC_API_KEY        Required for Claude Code"
            echo "  OPENAI_API_KEY           Required for Causeway embeddings"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Load .env file if it exists (check multiple locations)
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "Loading environment from $SCRIPT_DIR/.env"
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Also check project root .env
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "Loading environment from $PROJECT_DIR/.env"
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Also check causeway package .env (where setup stores keys)
if [ -f "$PROJECT_DIR/causeway/.env" ]; then
    echo "Loading environment from $PROJECT_DIR/causeway/.env"
    set -a
    source "$PROJECT_DIR/causeway/.env"
    set +a
fi

# Check for required API keys
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}ERROR: ANTHROPIC_API_KEY is not set${NC}"
    echo "Set it in your environment or create a .env file in tests/e2e/"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}ERROR: OPENAI_API_KEY is not set${NC}"
    echo "Set it in your environment or create a .env file in tests/e2e/"
    exit 1
fi

echo -e "${GREEN}API keys configured${NC}"

# Create logs directory
mkdir -p "$LOG_DIR"

# Check if Docker image exists or force rebuild
IMAGE_EXISTS=$(docker images -q "$IMAGE_NAME" 2>/dev/null)

if [ -z "$IMAGE_EXISTS" ] || [ "$FORCE_BUILD" = true ]; then
    echo ""
    echo "Building Docker image..."
    docker build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Dockerfile" "$PROJECT_DIR"
    echo -e "${GREEN}Docker image built successfully${NC}"
else
    echo -e "${YELLOW}Using existing Docker image (use --build to rebuild)${NC}"
fi

echo ""
echo "========================================"
echo "  Running E2E Tests"
echo "========================================"
echo ""

# Build docker run command
DOCKER_CMD=(
    docker run --rm
    -e "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
    -e "OPENAI_API_KEY=$OPENAI_API_KEY"
    -e "LOG_DIR=/e2e/logs"
    -v "$LOG_DIR:/e2e/logs"
)

# Add specific scenario if provided
if [ -n "$SPECIFIC_SCENARIO" ]; then
    # Override entrypoint to run specific scenario
    DOCKER_CMD+=(
        --entrypoint /bin/bash
        "$IMAGE_NAME"
        -c "cd /test-project && /e2e/cleanup_state.sh && \
            CAUSEWAY_CWD=/test-project uv run --directory /causeway causeway connect && \
            CAUSEWAY_CWD=/test-project uv run --directory /causeway causeway add python-safety && \
            CAUSEWAY_CWD=/test-project uv run --directory /causeway causeway add sysadmin-safety && \
            python3 /e2e/run_scenario.py /e2e/scenarios/${SPECIFIC_SCENARIO}.yml"
    )
else
    DOCKER_CMD+=("$IMAGE_NAME")
fi

# Run the container
"${DOCKER_CMD[@]}"
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All E2E tests passed!${NC}"
else
    echo -e "${RED}E2E tests failed!${NC}"
    echo ""
    echo "Logs are available in: $LOG_DIR"
    echo "Database files copied on failure for debugging."
fi

exit $EXIT_CODE
