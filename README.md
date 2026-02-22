# minbot: Minimal Telegram Bot for GitHub Development

A lightweight Telegram bot that monitors GitHub issues, estimates difficulty/urgency, suggests what to work on, and can autonomously work on issues using Claude Code.

## Quick Start

**1. Install**

```bash
curl -fsSL https://raw.githubusercontent.com/ChicagoHAI/minbot/main/install.sh | bash
```

Or clone and run locally:

```bash
git clone git@github.com:ChicagoHAI/minbot.git
cd minbot
bash install.sh
```

This installs prerequisites (`uv`, `claude` CLI) if missing, checks for `gh`, clones the repo, and runs `uv sync`.

**2. Get your tokens**

| Token | Where to get it |
|-------|----------------|
| GitHub Token | [github.com/settings/tokens](https://github.com/settings/tokens) (scopes: `repo`) |
| Telegram Bot Token | Talk to [@BotFather](https://t.me/BotFather) on Telegram |
| Telegram Chat ID | Send a message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` |

**3. Configure**

```bash
uv run python -m minbot setup
```

This prompts for your GitHub token, Telegram token, chat ID, and repos (in `owner/repo` format). Config is saved to `~/.minbot/config.json`.

You can also create the config file manually:

```json
{
  "telegram_token": "your-telegram-bot-token",
  "telegram_chat_id": 123456789,
  "github_token": "ghp_...",
  "github_repos": ["owner/repo", "owner/repo2"],
  "check_interval_hours": 6,
  "workspace_dir": "/workspace"
}
```

Optionally add `"anthropic_api_key": "sk-ant-..."` to use the Anthropic SDK instead of the `claude` CLI for issue analysis.

**5. Run**

```bash
uv run minbot
```

Open Telegram and send `/start` to your bot.

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

## Docker

```bash
docker compose up --build
```

Mount your config into the container or set environment variables. Edit `docker-compose.yml` to add:

```yaml
services:
  minbot:
    environment:
      - ANTHROPIC_API_KEY=sk-ant-...
    volumes:
      - ~/.minbot:/root/.minbot
```

## Running Tests

```bash
uv run pytest tests/ -v
```

## Project Structure

```
minbot/
  config.py      # Config loading from ~/.minbot/config.json
  github.py      # GitHub operations via gh CLI
  agent.py       # LLM reasoning via SDK or CLI (issue triage, suggestions)
  worker.py      # Claude Code subprocess for coding
  scheduler.py   # Periodic issue checking and proactive suggestions
  bot.py         # Telegram bot handlers (entry point)
```
