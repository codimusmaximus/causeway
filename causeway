#!/usr/bin/env python3
"""Causeway CLI - rule enforcement for Claude Code."""
import json
import os
import subprocess
import sys
from pathlib import Path

CAUSEWAY_DIR = Path(__file__).parent.resolve()
ORIG_CWD = os.environ.get("CAUSEWAY_CWD") or os.getcwd()

# Re-exec with uv if dependencies missing
try:
    import sqlite_vec
except ImportError:
    env = os.environ.copy()
    env["CAUSEWAY_CWD"] = ORIG_CWD
    os.chdir(CAUSEWAY_DIR)
    os.execvpe("uv", ["uv", "run", "python3", __file__] + sys.argv[1:], env)

def cmd_init():
    """Initialize causeway in current directory."""
    # Init database
    sys.path.insert(0, str(CAUSEWAY_DIR))
    from db import init_db
    init_db()
    print("Initialized causeway database")

def cmd_connect():
    """Connect causeway to Claude Code."""
    project_path = Path(ORIG_CWD)

    # 1. Add hooks to current project
    settings_path = project_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    settings = {}
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())

    hooks = settings.setdefault("hooks", {})

    # Pre-tool hook: check rules before execution
    hooks["PreToolUse"] = [
        {
            "matcher": "",
            "hooks": [{"type": "command", "command": f"uv run --directory {CAUSEWAY_DIR} python3 {CAUSEWAY_DIR}/scripts/check_rules.py"}]
        }
    ]

    # Stop hook: learn from session after it ends
    hooks["Stop"] = [
        {
            "matcher": "",
            "hooks": [{"type": "command", "command": f"uv run --directory {CAUSEWAY_DIR} python3 {CAUSEWAY_DIR}/learning_agent.py"}]
        }
    ]

    settings_path.write_text(json.dumps(settings, indent=2))
    print(f"Added hooks to {settings_path}")

    # 2. Add MCP server globally
    mcp_path = Path.home() / ".claude" / "mcp_servers.json"
    mcp_path.parent.mkdir(parents=True, exist_ok=True)

    servers = {}
    if mcp_path.exists():
        servers = json.loads(mcp_path.read_text())

    servers["causeway"] = {
        "command": "uv",
        "args": ["run", "--directory", str(CAUSEWAY_DIR), "python3", str(CAUSEWAY_DIR / "brain_mcp.py")],
        "env": {"CAUSEWAY_DB": str(CAUSEWAY_DIR / "brain.db")}
    }

    mcp_path.write_text(json.dumps(servers, indent=2))
    print(f"Added MCP server to {mcp_path}")

    # 3. Also add project-level .mcp.json
    project_mcp = project_path / ".mcp.json"
    project_servers = {}
    if project_mcp.exists():
        project_servers = json.loads(project_mcp.read_text())

    mcp_servers = project_servers.setdefault("mcpServers", {})
    mcp_servers["causeway"] = {
        "type": "stdio",
        "command": "uv",
        "args": ["run", "--directory", str(CAUSEWAY_DIR), "python3", str(CAUSEWAY_DIR / "brain_mcp.py")],
        "env": {"CAUSEWAY_DB": str(CAUSEWAY_DIR / "brain.db")}
    }

    project_mcp.write_text(json.dumps(project_servers, indent=2))
    print(f"Added MCP server to {project_mcp}")

    print("\nRestart Claude Code to activate.")

def cmd_add(ruleset: str):
    """Add a predefined ruleset."""
    rulesets = {
        "python-safety": [
            {"type": "regex", "pattern": r"^pip3? install", "description": "Use uv instead of pip", "action": "warn", "tool": "Bash", "solution": "uv pip install"},
            {"type": "regex", "pattern": r"^python [^3]", "description": "Use python3 explicitly", "action": "warn", "tool": "Bash", "solution": "python3"},
            {"type": "regex", "pattern": r"rm -rf /", "description": "Dangerous rm command", "action": "block", "tool": "Bash"},
        ],
        "git-safety": [
            {"type": "regex", "pattern": r"git push.*(--force|-f)", "description": "No force push", "action": "block", "tool": "Bash"},
            {"type": "regex", "pattern": r"git reset --hard", "description": "Dangerous reset", "action": "warn", "tool": "Bash"},
        ],
        "secrets": [
            {"type": "regex", "pattern": r"(api[_-]?key|secret|password|token)\s*[=:]\s*['\"][^'\"]+['\"]", "description": "Hardcoded secret detected", "action": "block"},
        ],
    }

    if ruleset not in rulesets:
        print(f"Unknown ruleset: {ruleset}")
        print(f"Available: {', '.join(rulesets.keys())}")
        sys.exit(1)

    sys.path.insert(0, str(CAUSEWAY_DIR))
    from db import get_connection, init_db
    init_db()

    conn = get_connection()
    for rule in rulesets[ruleset]:
        conn.execute("""
            INSERT INTO rules (type, pattern, description, action, tool, solution, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (rule.get("type"), rule.get("pattern"), rule.get("description"),
              rule.get("action", "block"), rule.get("tool"), rule.get("solution")))
    conn.commit()
    conn.close()

    print(f"Added {len(rulesets[ruleset])} rules from '{ruleset}'")

def cmd_list():
    """List active rules."""
    sys.path.insert(0, str(CAUSEWAY_DIR))
    from db import get_connection, init_db
    init_db()

    conn = get_connection()
    rows = conn.execute("SELECT id, type, action, description FROM rules WHERE active = 1 ORDER BY id").fetchall()
    conn.close()

    if not rows:
        print("No active rules")
        return

    for r in rows:
        print(f"#{r['id']:3} [{r['action']:5}] {r['description']}")

def cmd_ui():
    """Start the dashboard UI."""
    os.chdir(CAUSEWAY_DIR)
    os.execvp("python3", ["python3", "server.py"])

def main():
    usage = """causeway - rule enforcement for Claude Code

Commands:
    init        Initialize database
    connect     Add hooks & MCP to Claude Code (run from your project)
    add <set>   Add a ruleset (python-safety, git-safety, secrets)
    list        List active rules
    ui          Start dashboard at localhost:8000
"""

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "init":
        cmd_init()
    elif cmd == "connect":
        cmd_connect()
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: causeway add <ruleset>")
            print("Available: python-safety, git-safety, secrets")
            sys.exit(1)
        cmd_add(sys.argv[2])
    elif cmd == "list":
        cmd_list()
    elif cmd == "ui":
        cmd_ui()
    else:
        print(f"Unknown command: {cmd}")
        print(usage)
        sys.exit(1)

if __name__ == "__main__":
    main()
