#!/bin/bash
# cleanup_state.sh - Reset state between E2E test scenarios
#
# Removes:
#   - .causeway/ directory (brain.db, etc)
#   - .claude/ directory (settings.json with hooks)
#   - .mcp.json file
#   - Any test files created by scenarios

set -e

PROJECT_DIR="${CAUSEWAY_CWD:-/test-project}"

echo "Cleaning up state in $PROJECT_DIR..."

# Remove causeway state
rm -rf "$PROJECT_DIR/.causeway"

# Remove Claude Code settings/hooks
rm -rf "$PROJECT_DIR/.claude"

# Remove MCP config
rm -f "$PROJECT_DIR/.mcp.json"

# Remove any test files that scenarios might have created
rm -f "$PROJECT_DIR/test-file.txt"
rm -f "$PROJECT_DIR/test-script.py"
rm -f "$PROJECT_DIR/dangerous-file.sh"
rm -rf "$PROJECT_DIR/test-dir"

# Reset git to clean state (ignore errors if no commits)
cd "$PROJECT_DIR"
git reset --hard HEAD 2>/dev/null || true
git clean -fd 2>/dev/null || true

echo "Cleanup complete."
