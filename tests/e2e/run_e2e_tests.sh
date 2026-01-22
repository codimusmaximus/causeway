#!/bin/bash
# run_e2e_tests.sh - Main E2E test orchestrator
#
# Iterates through all scenario YAML files and executes them sequentially.
# For each scenario:
#   1. Clean up state (remove .causeway/, .claude/, etc.)
#   2. Run 'causeway connect' to initialize hooks
#   3. Add required rulesets (python-safety, sysadmin-safety)
#   4. Run the scenario using run_scenario.py
#   5. Track results

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${CAUSEWAY_CWD:-/test-project}"
CAUSEWAY_DIR="${CAUSEWAY_ROOT:-/causeway}"
LOG_DIR="${LOG_DIR:-/e2e/logs}"
SCENARIOS_DIR="${SCRIPT_DIR}/scenarios"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
SKIPPED=0
TOTAL=0

# Create log directory
mkdir -p "$LOG_DIR"

echo ""
echo "========================================"
echo "  Causeway E2E Test Suite"
echo "========================================"
echo ""
echo "Project directory: $PROJECT_DIR"
echo "Causeway directory: $CAUSEWAY_DIR"
echo "Scenarios directory: $SCENARIOS_DIR"
echo ""

# Check for required API keys
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}ERROR: ANTHROPIC_API_KEY is not set${NC}"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}ERROR: OPENAI_API_KEY is not set${NC}"
    exit 1
fi

echo -e "${GREEN}API keys configured${NC}"
echo ""

# Function to run a single scenario
run_scenario() {
    local scenario_file="$1"
    local scenario_name=$(basename "$scenario_file" .yml)

    echo "----------------------------------------"
    echo -e "${BLUE}Running: $scenario_name${NC}"
    echo "----------------------------------------"

    # Step 1: Clean up state
    echo "  [1/4] Cleaning up state..."
    "$SCRIPT_DIR/cleanup_state.sh" > "$LOG_DIR/${scenario_name}_cleanup.log" 2>&1

    # Step 2: Run causeway connect
    echo "  [2/4] Running causeway connect..."
    cd "$PROJECT_DIR"

    # Create .env file for causeway with OpenAI key (non-interactive setup)
    mkdir -p "$CAUSEWAY_DIR/causeway"
    cat > "$CAUSEWAY_DIR/causeway/.env" << EOF
OPENAI_API_KEY=$OPENAI_API_KEY
CAUSEWAY_PROVIDER=openai
CAUSEWAY_CALL_HOME=false
EOF

    # Run causeway connect (will use the .env we created)
    CAUSEWAY_CWD="$PROJECT_DIR" uv run --directory "$CAUSEWAY_DIR" causeway connect > "$LOG_DIR/${scenario_name}_connect.log" 2>&1

    # Step 3: Add rulesets
    echo "  [3/4] Adding rulesets..."
    CAUSEWAY_CWD="$PROJECT_DIR" uv run --directory "$CAUSEWAY_DIR" causeway add python-safety >> "$LOG_DIR/${scenario_name}_connect.log" 2>&1
    CAUSEWAY_CWD="$PROJECT_DIR" uv run --directory "$CAUSEWAY_DIR" causeway add sysadmin-safety >> "$LOG_DIR/${scenario_name}_connect.log" 2>&1

    # Step 4: Run the scenario
    echo "  [4/4] Executing scenario..."
    local exit_code=0
    python3 "$SCRIPT_DIR/run_scenario.py" "$scenario_file" > "$LOG_DIR/${scenario_name}_scenario.log" 2>&1 || exit_code=$?

    # Process result
    if [ $exit_code -eq 0 ]; then
        echo -e "  ${GREEN}PASSED${NC}"
        ((PASSED++))
    elif [ $exit_code -eq 2 ]; then
        echo -e "  ${YELLOW}SKIPPED (optional)${NC}"
        ((SKIPPED++))
    else
        echo -e "  ${RED}FAILED${NC}"
        ((FAILED++))

        # Copy brain.db for debugging
        if [ -f "$PROJECT_DIR/.causeway/brain.db" ]; then
            cp "$PROJECT_DIR/.causeway/brain.db" "$LOG_DIR/${scenario_name}_brain.db"
        fi

        # Show last few lines of scenario log
        echo ""
        echo "  Last output:"
        tail -10 "$LOG_DIR/${scenario_name}_scenario.log" | sed 's/^/    /'
        echo ""
    fi

    ((TOTAL++))
    return $exit_code
}

# Find and sort scenario files
SCENARIO_FILES=$(find "$SCENARIOS_DIR" -name "*.yml" -type f | sort)

if [ -z "$SCENARIO_FILES" ]; then
    echo -e "${RED}ERROR: No scenario files found in $SCENARIOS_DIR${NC}"
    exit 1
fi

# Count scenarios
NUM_SCENARIOS=$(echo "$SCENARIO_FILES" | wc -l | tr -d ' ')
echo "Found $NUM_SCENARIOS scenario(s) to run"
echo ""

# Run each scenario
for scenario_file in $SCENARIO_FILES; do
    run_scenario "$scenario_file" || true  # Continue on failure
done

# Print summary
echo ""
echo "========================================"
echo "  Summary"
echo "========================================"
echo ""
echo -e "  Total:   $TOTAL"
echo -e "  ${GREEN}Passed:  $PASSED${NC}"
echo -e "  ${RED}Failed:  $FAILED${NC}"
echo -e "  ${YELLOW}Skipped: $SKIPPED${NC}"
echo ""

# Exit with appropriate code
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}E2E tests failed!${NC}"
    exit 1
else
    echo -e "${GREEN}All E2E tests passed!${NC}"
    exit 0
fi
