#!/usr/bin/env python3
"""Causeway CLI - rule enforcement for Claude Code."""
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

API_URL = "https://causeway-api.fly.dev"
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

CAUSEWAY_DIR = Path(__file__).parent.resolve()  # Package dir: ~/.causeway/causeway
CAUSEWAY_ROOT = CAUSEWAY_DIR.parent  # Project root: ~/.causeway (where pyproject.toml is)
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
    from rich.console import Console
    console = Console()

    project_path = Path(ORIG_CWD)
    causeway_dir = project_path / ".causeway"
    db_path = causeway_dir / "brain.db"

    # Init database in project's .causeway/ folder
    sys.path.insert(0, str(CAUSEWAY_DIR))
    from db import init_db
    init_db(db_path)

    console.print(f"[green]✓[/green] Initialized database at [dim]{db_path}[/dim]")

def load_config():
    """Load existing config from global .env file."""
    env_file = CAUSEWAY_DIR / ".env"
    config = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()
    return config


def save_config(config: dict):
    """Save config to global .env file."""
    env_file = CAUSEWAY_DIR / ".env"
    lines = [f"{k}={v}" for k, v in config.items()]
    env_file.write_text("\n".join(lines) + "\n")


def get_install_id():
    """Get or create install ID."""
    id_file = CAUSEWAY_DIR / ".install_id"
    if id_file.exists():
        return id_file.read_text().strip()
    import uuid
    install_id = str(uuid.uuid4())
    id_file.write_text(install_id)
    return install_id


def register_user(email: str, provider: str):
    """Register user with API (subscribes to updates)."""
    try:
        data = {
            "install_id": get_install_id(),
            "email": email,
            "source": "cli",
        }
        req = urllib.request.Request(
            f"{API_URL}/subscribe",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # Silent fail - don't block setup


def validate_api_key(provider: str, api_key: str) -> tuple[bool, str]:
    """Validate API key by making a test request."""
    try:
        if provider == "openai":
            req = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            urllib.request.urlopen(req, timeout=10)
            return True, "Valid"
        elif provider == "anthropic":
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps({
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}]
                }).encode(),
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            urllib.request.urlopen(req, timeout=10)
            return True, "Valid"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Invalid API key"
        elif e.code == 403:
            return False, "Access denied - check permissions"
        return False, f"Error: {e.code}"
    except Exception as e:
        return False, f"Connection error: {str(e)[:30]}"
    return False, "Unknown error"


def interactive_setup():
    """Interactive setup wizard for first-time users."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text

    console = Console()
    config = load_config()

    # Check if already configured
    if config.get("CAUSEWAY_EMAIL") and (config.get("OPENAI_API_KEY") or config.get("ANTHROPIC_API_KEY")):
        console.print("[dim]Already configured. Skipping setup.[/dim]\n")
        return config

    # Welcome banner
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Welcome to Causeway[/bold cyan]\n[dim]Rule enforcement for Claude Code[/dim]",
        border_style="cyan",
        padding=(1, 4)
    ))
    console.print()

    # Email
    email = config.get("CAUSEWAY_EMAIL", "")
    if not email:
        while True:
            email = Prompt.ask("[bold]Email[/bold] [dim](for updates & support)[/dim]")
            if EMAIL_REGEX.match(email):
                config["CAUSEWAY_EMAIL"] = email
                break
            console.print("[red]Please enter a valid email address.[/red]")
        console.print()

    # Provider selection
    provider = config.get("CAUSEWAY_PROVIDER", "")
    if not provider:
        console.print("[bold]Select your LLM provider[/bold] [dim](for rule evaluation)[/dim]\n")
        console.print("  [cyan]1[/cyan]  OpenAI [dim](recommended)[/dim]")
        console.print("  [cyan]2[/cyan]  Anthropic")
        console.print()
        while True:
            choice = Prompt.ask("Enter [cyan]1[/cyan] or [cyan]2[/cyan]")
            if choice == "1":
                provider = "openai"
                break
            elif choice == "2":
                provider = "anthropic"
                break
            console.print("[red]Please enter 1 or 2.[/red]")
        config["CAUSEWAY_PROVIDER"] = provider
        console.print()

    # API Key
    if provider == "anthropic":
        key_name = "ANTHROPIC_API_KEY"
        key_display = "Anthropic"
    else:
        key_name = "OPENAI_API_KEY"
        key_display = "OpenAI"

    if not config.get(key_name):
        from rich.status import Status
        import getpass
        while True:
            api_key = getpass.getpass(f"{key_display} API key: ")
            if not api_key:
                console.print("[red]API key is required.[/red]")
                continue

            # Show masked version
            masked = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "*" * len(api_key)
            console.print(f"[dim]{masked}[/dim]")

            with Status("[dim]Validating...[/dim]", spinner="dots"):
                valid, msg = validate_api_key(provider, api_key)

            if valid:
                config[key_name] = api_key
                console.print(f"[green]\u2713[/green] Valid!")
                break
            else:
                console.print(f"[red]\u2717 {msg}[/red] - try again")
        console.print()

    save_config(config)

    # Register with API
    if email and provider:
        register_user(email, provider)

    console.print(Panel.fit(
        "[bold green]Configuration saved![/bold green]",
        border_style="green"
    ))
    console.print()

    return config


def cmd_connect():
    """Connect causeway to Claude Code globally."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    home = Path.home()

    # Interactive setup (global config - API keys, etc.)
    interactive_setup()

    # 1. Add global hooks to ~/.claude/settings.json
    settings_path = home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    settings = {}
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())

    hooks = settings.setdefault("hooks", {})

    # All hooks use bash wrapper to capture cwd before uv's --directory changes it
    uv_cmd = f"CAUSEWAY_CWD=$(pwd) uv run --directory {CAUSEWAY_ROOT}"

    # SessionStart hook: init DB in current folder + version check
    hooks["SessionStart"] = [
        {
            "matcher": "*",
            "hooks": [
                {"type": "command", "command": f"bash -c '{uv_cmd} causeway-init'"},
                {"type": "command", "command": f"bash {CAUSEWAY_DIR}/hooks/ping.sh"}
            ]
        }
    ]

    # Pre-tool hook: check rules before execution
    hooks["PreToolUse"] = [
        {
            "matcher": "*",
            "hooks": [{"type": "command", "command": f"bash -c '{uv_cmd} causeway-check'"}]
        }
    ]

    # Stop hook: learn from session after it ends
    hooks["Stop"] = [
        {
            "matcher": "*",
            "hooks": [{"type": "command", "command": f"bash -c '{uv_cmd} causeway-learn'"}]
        }
    ]

    settings_path.write_text(json.dumps(settings, indent=2))
    console.print(f"[green]\u2713[/green] Added global hooks to [dim]{settings_path}[/dim]")

    # 2. Add global MCP to ~/.mcp.json (uses bash wrapper to capture cwd before uv changes it)
    global_mcp = home / ".mcp.json"
    mcp_config = {}
    if global_mcp.exists():
        mcp_config = json.loads(global_mcp.read_text())

    mcp_servers = mcp_config.setdefault("mcpServers", {})
    mcp_servers["causeway"] = {
        "type": "stdio",
        "command": "bash",
        "args": ["-c", f"CAUSEWAY_CWD=$(pwd) uv run --directory {CAUSEWAY_ROOT} causeway-mcp"]
    }

    global_mcp.write_text(json.dumps(mcp_config, indent=2))
    console.print(f"[green]\u2713[/green] Added global MCP server to [dim]{global_mcp}[/dim]")

    console.print()
    console.print(Panel.fit(
        "[bold]Restart Claude Code to activate[/bold]\n[dim]Causeway will auto-init a database in each project folder[/dim]",
        border_style="cyan"
    ))

def cmd_rulesets():
    """List available rulesets."""
    sys.path.insert(0, str(CAUSEWAY_DIR))
    from rulesets import RULESETS

    for name, data in RULESETS.items():
        print(f"{name:20} {data['description']} ({len(data['rules'])} rules)")

def cmd_add(ruleset: str):
    """Add a predefined ruleset."""
    sys.path.insert(0, str(CAUSEWAY_DIR))
    from rulesets import RULESETS
    from db import get_connection, init_db

    if ruleset not in RULESETS:
        print(f"Unknown ruleset: {ruleset}")
        print(f"Available: {', '.join(RULESETS.keys())}")
        sys.exit(1)

    init_db()
    conn = get_connection()
    rules = RULESETS[ruleset]["rules"]

    for rule in rules:
        conn.execute("""
            INSERT INTO rules (type, pattern, description, action, tool, solution, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (rule.get("type"), rule.get("pattern"), rule.get("description"),
              rule.get("action", "block"), rule.get("tool"), rule.get("solution")))
    conn.commit()
    conn.close()

    print(f"Added {len(rules)} rules from '{ruleset}'")

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
    """Start the dashboard UI for the current project."""
    # Set CAUSEWAY_CWD so the server finds the right DB
    os.environ["CAUSEWAY_CWD"] = ORIG_CWD
    os.chdir(CAUSEWAY_ROOT)
    os.execvp("python3", ["python3", "-m", "causeway.server"])


def cmd_update():
    """Update causeway to the latest version."""
    from rich.console import Console
    console = Console()

    install_dir = Path.home() / ".causeway"

    if not install_dir.exists():
        console.print("[red]Causeway not installed at ~/.causeway[/red]")
        console.print("Run: curl -fsSL https://raw.githubusercontent.com/codimusmaximus/causeway/main/install.sh | bash")
        sys.exit(1)

    console.print("[cyan]Updating causeway...[/cyan]")

    # Check if it's a git repo
    git_dir = install_dir / ".git"
    if git_dir.exists():
        # Pull latest
        result = subprocess.run(
            ["git", "fetch", "--quiet"],
            cwd=install_dir,
            capture_output=True
        )
        if result.returncode != 0:
            console.print(f"[red]Git fetch failed[/red]")
            sys.exit(1)

        result = subprocess.run(
            ["git", "reset", "--hard", "origin/main", "--quiet"],
            cwd=install_dir,
            capture_output=True
        )
        if result.returncode != 0:
            console.print(f"[red]Git reset failed[/red]")
            sys.exit(1)

        console.print("[green]✓[/green] Pulled latest from git")
    else:
        console.print("[yellow]Not a git repo - re-cloning...[/yellow]")
        # Backup and re-clone
        import shutil
        backup = install_dir.with_name(".causeway.bak")
        if backup.exists():
            shutil.rmtree(backup)
        shutil.move(install_dir, backup)

        result = subprocess.run(
            ["git", "clone", "--quiet", "https://github.com/codimusmaximus/causeway.git", str(install_dir)],
            capture_output=True
        )
        if result.returncode != 0:
            # Restore backup
            shutil.move(backup, install_dir)
            console.print(f"[red]Clone failed[/red]")
            sys.exit(1)

        # Copy over .env if it existed
        old_env = backup / "causeway" / ".env"
        new_env = install_dir / "causeway" / ".env"
        if old_env.exists():
            shutil.copy(old_env, new_env)

        shutil.rmtree(backup)
        console.print("[green]✓[/green] Re-cloned from git")

    # Re-sync dependencies
    console.print("[dim]Installing dependencies...[/dim]")
    result = subprocess.run(
        ["uv", "sync", "--quiet"],
        cwd=install_dir,
        capture_output=True
    )
    if result.returncode != 0:
        # Try without --quiet for error info
        subprocess.run(["uv", "sync"], cwd=install_dir)

    console.print("[green]✓[/green] Dependencies updated")
    console.print("\n[bold green]Update complete![/bold green]")


def cmd_setup(reset: bool = False):
    """Run setup wizard. Use --reset to reconfigure everything."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.status import Status

    console = Console()
    config = load_config()

    if reset:
        # Clear config but keep install_id
        config = {}
        save_config(config)
        console.print("[yellow]Configuration reset.[/yellow]\n")

    # Show current config if exists
    if config.get("CAUSEWAY_EMAIL") or config.get("CAUSEWAY_PROVIDER"):
        console.print(Panel.fit(
            f"[bold]Current Configuration[/bold]\n\n"
            f"Email:    [cyan]{config.get('CAUSEWAY_EMAIL', '[not set]')}[/cyan]\n"
            f"Provider: [cyan]{config.get('CAUSEWAY_PROVIDER', '[not set]')}[/cyan]\n"
            f"API Key:  [cyan]{'configured' if config.get('OPENAI_API_KEY') or config.get('ANTHROPIC_API_KEY') else '[not set]'}[/cyan]",
            border_style="dim"
        ))
        console.print()

        if not Confirm.ask("Reconfigure?", default=False):
            return

        # Clear for reconfiguration
        config.pop("CAUSEWAY_EMAIL", None)
        config.pop("CAUSEWAY_PROVIDER", None)
        config.pop("OPENAI_API_KEY", None)
        config.pop("ANTHROPIC_API_KEY", None)

    # Run the setup wizard
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Causeway Setup[/bold cyan]\n[dim]Rule enforcement for Claude Code[/dim]",
        border_style="cyan",
        padding=(1, 4)
    ))
    console.print()

    # Email
    while True:
        email = Prompt.ask("[bold]Email[/bold] [dim](for updates & support)[/dim]")
        if EMAIL_REGEX.match(email):
            config["CAUSEWAY_EMAIL"] = email
            break
        console.print("[red]Please enter a valid email address.[/red]")
    console.print()

    # Provider
    console.print("[bold]Select your LLM provider[/bold] [dim](for rule evaluation)[/dim]\n")
    console.print("  [cyan]1[/cyan]  OpenAI [dim](recommended)[/dim]")
    console.print("  [cyan]2[/cyan]  Anthropic")
    console.print()
    while True:
        choice = Prompt.ask("Enter [cyan]1[/cyan] or [cyan]2[/cyan]")
        if choice == "1":
            provider = "openai"
            break
        elif choice == "2":
            provider = "anthropic"
            break
        console.print("[red]Please enter 1 or 2.[/red]")
    config["CAUSEWAY_PROVIDER"] = provider
    console.print()

    # API Key
    key_name = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
    key_display = "Anthropic" if provider == "anthropic" else "OpenAI"

    import getpass
    while True:
        api_key = getpass.getpass(f"{key_display} API key: ")
        if not api_key:
            console.print("[red]API key is required.[/red]")
            continue

        # Show masked version
        masked = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "*" * len(api_key)
        console.print(f"[dim]{masked}[/dim]")

        with Status("[dim]Validating...[/dim]", spinner="dots"):
            valid, msg = validate_api_key(provider, api_key)

        if valid:
            config[key_name] = api_key
            console.print(f"[green]\u2713[/green] Valid!")
            break
        else:
            console.print(f"[red]\u2717 {msg}[/red] - try again")
    console.print()

    save_config(config)
    register_user(email, provider)

    console.print(Panel.fit(
        "[bold green]Configuration saved![/bold green]",
        border_style="green"
    ))

def main():
    usage = """causeway - rule enforcement for Claude Code

Commands:
    connect        Add hooks & MCP to Claude Code (run once, works globally)
    update         Update causeway to the latest version
    setup          Reconfigure email, provider, and API key
    setup --reset  Reset all configuration
    list           List active rules
    rulesets       List available rulesets
    add <set>      Add a ruleset
    ui             Start dashboard at localhost:8000
"""

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "init":
        cmd_init()
    elif cmd == "connect":
        cmd_connect()
    elif cmd == "update":
        cmd_update()
    elif cmd == "setup":
        reset = "--reset" in sys.argv
        cmd_setup(reset=reset)
    elif cmd == "rulesets":
        cmd_rulesets()
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: causeway add <ruleset>")
            cmd_rulesets()
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
