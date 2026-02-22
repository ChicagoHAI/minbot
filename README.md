# minbot: Minimal Telegram Bot for GitHub Development

A lightweight Telegram bot that monitors GitHub issues, estimates difficulty/urgency, suggests what to work on, and can autonomously work on issues using Claude Code.

## Quick Start

**1. Get your tokens**

| Token | Where to get it |
|-------|----------------|
| GitHub Token | [github.com/settings/tokens](https://github.com/settings/tokens) (scopes: `repo`) |
| Telegram Bot Token | Talk to [@BotFather](https://t.me/BotFather) on Telegram |

**2. Clone and configure**

```bash
git clone git@github.com:ChicagoHAI/minbot.git
cd minbot
```

Create `~/.minbot/config.json`:

```json
{
  "telegram_token": "your-telegram-bot-token",
  "github_token": "ghp_...",
  "github_repos": ["owner/repo", "owner/repo2"]
}
```

Optionally add `"anthropic_api_key": "sk-ant-..."` to use the Anthropic SDK instead of the `claude` CLI for issue analysis.

**3. Run**

```bash
docker compose up --build -d
```

This builds the image (installs Python deps, Claude CLI) and starts the bot. Your config and SSH keys are mounted into the container automatically.

Open Telegram and send `/start` to your bot. The bot captures your chat ID automatically on first interaction.

## Running without Docker

One-liner:

```bash
curl -fsSL https://raw.githubusercontent.com/ChicagoHAI/minbot/main/install.sh | bash
```

Or clone and install manually:

```bash
git clone git@github.com:ChicagoHAI/minbot.git
cd minbot
bash install.sh
```

Then configure and run:

```bash
uv run python -m minbot setup      # interactive config
uv run minbot                      # start the bot
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show available commands |
| `/issues` | List open issues with difficulty/urgency estimates |
| `/suggest` | Get a recommendation on what to work on next |
| `/work <number>` | Work on an issue (single repo) |
| `/work <repo> <number>` | Work on an issue in a specific repo |
| `/repos` | List configured repos |
| `/status` | Check progress of current work |

## How `/work` works

When you send `/work 42`, minbot will:

1. Clone/pull the repo into `workspace_dir/<owner>/<repo>`
2. Create a branch `issue-42`
3. Spawn Claude Code CLI with the issue context
4. Claude Code makes changes, commits, and pushes
5. minbot creates a PR and sends you the link

## Issue Analysis

minbot uses Claude to analyze issues and suggest what to work on. It supports two modes:

- **Claude CLI** (default): Calls the `claude` CLI as a subprocess. Requires `claude` to be installed and authenticated.
- **Anthropic SDK**: Set `anthropic_api_key` in config.

## Running Tests

```bash
uv run pytest tests/ -v
```

## Project Structure

```
minbot/
  config.py      # Config loading from ~/.minbot/config.json
  github.py      # GitHub operations via PyGithub + git
  agent.py       # LLM reasoning via SDK or CLI (issue triage, suggestions)
  worker.py      # Claude Code subprocess for coding
  scheduler.py   # Periodic issue checking and proactive suggestions
  bot.py         # Telegram bot handlers (entry point)
```
