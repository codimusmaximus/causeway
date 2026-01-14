# Running Causeway in a DevContainer

This guide explains how to run Claude Code with Causeway in a secure, isolated Docker container.

## Why Use a DevContainer?

- **Security**: Restrictive firewall limits network access to only essential services
- **Isolation**: Keeps your development environment separate from your main system
- **Persistence**: Named volumes preserve your Claude config, Causeway rules, and shell history
- **Reproducibility**: Same environment every time you spin up

## Quick Start

```bash
# Clone or copy the devcontainer files
cd your-project
cp -r path/to/devcontainer .devcontainer

# Run the container
./.devcontainer/run.sh

# Inside the container:
sudo /usr/local/bin/init-firewall.sh
causeway connect
claude --dangerously-skip-permissions
```

## What's Included

| File | Purpose |
|------|---------|
| `devcontainer.json` | VS Code devcontainer config (optional) |
| `Dockerfile` | Container image with Node.js, Python, Claude Code, and Causeway |
| `init-firewall.sh` | Restrictive firewall allowing only whitelisted domains |
| `run.sh` | Helper script to build and run the container |

## Persistent Volumes

The setup uses named Docker volumes to persist data across container restarts:

| Volume | Path | Purpose |
|--------|------|---------|
| `claude-code-config` | `/home/node/.claude` | Claude Code credentials & settings |
| `claude-code-history` | `/commandhistory` | Shell command history |
| `causeway-data` | `/home/node/.causeway` | Causeway rules & configuration |

## Network Security

The firewall restricts outbound connections to:

- `registry.npmjs.org` - npm packages
- `api.anthropic.com` - Claude API
- `github.com` - GitHub (for git operations)
- `sentry.io` - Error reporting
- `statsig.anthropic.com` / `statsig.com` - Feature flags
- `marketplace.visualstudio.com` / `vscode.blob.core.windows.net` - VS Code extensions

All other outbound traffic is blocked.

## Causeway UI

Access the Causeway dashboard:

```bash
# Inside the container
causeway ui

# Access from host browser
open http://localhost:8080
```

## Commands Reference

```bash
# Start container (stops existing if running)
./.devcontainer/run.sh

# Restart existing container
docker start -ai claude-sandbox

# Stop container
docker stop claude-sandbox

# View logs
docker logs claude-sandbox

# Remove container (volumes persist)
docker rm claude-sandbox

# List volumes
docker volume ls | grep -E "(claude|causeway)"

# Remove all data (start fresh)
docker volume rm claude-code-config claude-code-history causeway-data
```

## Customization

### Change Port

Edit `run.sh` and modify the `-p` flag:

```bash
-p 9000:8000 \  # Causeway UI on localhost:9000
```

### Add Allowed Domains

Edit `init-firewall.sh` and add domains to the allowlist:

```bash
for domain in \
    "registry.npmjs.org" \
    "api.anthropic.com" \
    "your-custom-domain.com" \  # Add here
    ...
```

### Mount Additional Directories

Edit `run.sh` to add more volume mounts:

```bash
-v "$HOME/.ssh:/home/node/.ssh:ro" \  # SSH keys (read-only)
-v "$HOME/.gitconfig:/home/node/.gitconfig:ro" \  # Git config
```

## Troubleshooting

### Port Already in Use

```bash
# Find what's using the port
lsof -i :8080

# Change port in run.sh
-p 8081:8000 \
```

### Container Won't Start

```bash
# Check for existing container
docker ps -a | grep claude-sandbox

# Force remove
docker rm -f claude-sandbox
```

### Firewall Blocking Needed Service

Check `/usr/local/bin/init-firewall.sh` and add the domain to the allowlist, then rebuild:

```bash
docker rm claude-sandbox
./.devcontainer/run.sh
```
