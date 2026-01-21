<div align="center">

# Causeway

A self-learning hooks system for Claude Code.

[![Install](https://img.shields.io/badge/Install-blue?style=for-the-badge)](#install)

</div>

Causeway watches your Claude Code sessions and automatically learns your preferences. When you correct Claude or express a preference, Causeway captures it as a rule and enforces it in future sessions.

![Causeway Dashboard](docs/screen.png)

## How It Works

Causeway hooks into Claude Code's pre-tool and stop events. When a session ends, it analyzes the conversation for corrections or preferences and creates rules. Before each tool call, it checks those rules and blocks or warns Claude if needed.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/codimusmaximus/causeway/main/install.sh | bash
```

## Setup

1. Configure your API key (required for learning agent):

```bash
causeway setup
```

2. Connect Causeway to your project:

```bash
cd your-project
causeway connect
```

3. Restart Claude Code to activate.

## CLI Reference

```bash
causeway connect              # Add hooks + MCP to current project
causeway list                 # List active rules
causeway rulesets             # List available rulesets
causeway add <set>            # Add a predefined ruleset
causeway ui                   # Start dashboard at localhost:8000
causeway setup                # Configure email and API key
causeway setup --reset        # Reset all configuration
causeway config               # Show current configuration
causeway config call-home on  # Enable/disable telemetry
causeway update               # Update to latest release
causeway update --edge        # Update to latest main branch
causeway version              # Show version information
```

## Managing Rules

Rules can be managed through Claude using MCP tools. Causeway exposes tools that Claude can call directly.

### Adding Rules

Ask Claude to add a rule:

```
"Add a rule to block any DROP TABLE commands"
```

Claude will use the `add_rule` tool:

```
# Regex rule (fast pattern matching)
add_rule(
  type="regex",
  pattern="DROP\\s+TABLE",
  description="Block DROP TABLE commands",
  action="block",
  tool="Bash"
)

# Semantic rule (LLM-evaluated preferences)
add_rule(
  type="semantic",
  description="Prefer functional programming style over classes",
  problem="Code uses class-based patterns when functional would be cleaner",
  solution="Use pure functions, avoid mutable state",
  action="warn"
)
```

### Updating Rules

```
"Update rule #3 to warn instead of block"
```

Claude will use the `update_rule` tool:

```
update_rule(id=3, action="warn")
update_rule(id=5, description="New description", pattern="new_pattern")
```

### Deleting Rules

```
"Delete rule #7"
```

Claude will use the `delete_rule` tool:

```
delete_rule(id=7)
```

### Toggling Rules

```
"Disable rule #4 temporarily"
```

Claude will use the `toggle_rule` tool:

```
toggle_rule(id=4, active=false)   # Disable
toggle_rule(id=4, active=true)    # Re-enable
```

### Listing and Searching Rules

```
"Show me all active rules"
"Search for rules about database"
```

Claude can use `list_rules` and `search_rules`:

```
list_rules()                        # All active rules
list_rules(active_only=false)       # Include disabled rules
list_rules(type="regex")            # Only regex rules
search_rules(query="database")      # Semantic search
```

## Rule Types

| Type | When to Use | Speed |
|------|-------------|-------|
| `regex` | Exact patterns (commands, file paths, keywords) | Fast |
| `semantic` | Preferences, coding style, architectural decisions | Slower (LLM) |

## Actions

| Action | Behavior |
|--------|----------|
| `block` | Stops the tool call, Claude must try again |
| `warn` | Allows but notifies Claude of the preference |
| `log` | Silent logging for analytics |

## Telemetry

Causeway pings our API to track installs and check for updates. See [`causeway/hooks/ping.sh`](causeway/hooks/ping.sh)
