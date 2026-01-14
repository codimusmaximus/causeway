# causeway

Rule-based enforcement and learning for Claude Code.

## Quick Start

```bash
cd your-project
/path/to/causeway/causeway connect
```

This adds:
- **Pre-hook**: Checks rules before every tool call
- **Stop-hook**: Learns from session after it ends
- **MCP server**: Manage rules via Claude

Restart Claude Code to activate.

## CLI

```bash
causeway connect     # Add hooks + MCP to current project
causeway init        # Initialize database
causeway list        # List active rules
causeway add <set>   # Add ruleset (python-safety, git-safety, secrets)
causeway ui          # Start dashboard at localhost:8000
```

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code Session                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Tool Call ──► PreToolUse Hook ──► check_rules.py           │
│                     │                                       │
│                     ▼                                       │
│              ┌─────────────┐                                │
│              │ Regex Rules │ ──► Block/Warn/Allow           │
│              └─────────────┘                                │
│                                                             │
│  Session End ──► Stop Hook ──► learning_agent.py (async)    │
│                     │                                       │
│                     ▼                                       │
│              ┌─────────────┐                                │
│              │  LLM Agent  │ ──► Create/Update Rules        │
│              └─────────────┘                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Pre-Hook (check_rules.py)
- Runs before every tool call
- Fast regex pattern matching
- Blocks or warns based on rules
- Logs trace with timing

### Stop-Hook (learning_agent.py)
- Runs when session ends (async, non-blocking)
- Analyzes conversation for preferences/corrections
- Creates/updates rules automatically
- Links rules to source session

## Rule Types

**regex** - Fast pattern matching
```
pattern: "^pip3? "
action: block
tool: Bash
```

**semantic** - LLM-based matching
```
description: "Use Rich for terminal output"
action: warn
```

## Actions

- **block**: Stop tool call, return error
- **warn**: Stop tool call, return suggestion

Both stop execution - `warn` is softer language.

## Database

Single SQLite database tracks:
- **rules** - patterns, actions, source session
- **traces** - every hook execution with LLM prompt/response
- **sessions** - conversation history
- **projects** - folder paths

## Dashboard

```bash
causeway ui
# http://localhost:8000
```

- View/edit rules
- See traces (click to expand LLM prompt/response)
- Track rule origins (which session created it)

## Files

```
causeway/
├── causeway           # CLI entry point
├── db.py              # Database schema + migrations
├── server.py          # FastAPI dashboard
├── rule_agent.py      # Rule checking logic
├── learning_agent.py  # Post-session learning
├── brain_mcp.py       # MCP server for Claude
├── history_logger.py  # Session/message logging
└── scripts/
    └── check_rules.py # Pre-hook entry point
```
