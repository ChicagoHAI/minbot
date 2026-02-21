# minbot: Minimal Telegram Bot for GitHub Development

A lightweight Telegram bot that monitors GitHub issues, estimates difficulty/urgency, suggests what to work on, and can autonomously work on issues using Claude Code.

Core bot in just **~380 lines** of Python (run `bash core_lines.sh` to verify).

## Quick Start

**1. Install**

```bash
git clone https://github.com/chenhao/minbot.git
cd minbot
uv sync --extra dev
```

**2. Get your tokens**

You need three things:

| Token | Where to get it |
|-------|----------------|
| Telegram Bot Token | Talk to [@BotFather](https://t.me/BotFather) on Telegram |
| Telegram Chat ID | Send a message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` |
| Anthropic API Key | [console.anthropic.com](https://console.anthropic.com/) |

**3. Configure**

Create `~/.minbot/config.json`:

```json
{
  "telegram_token": "your-telegram-bot-token",
  "telegram_chat_id": 123456789,
  "github_repo": "owner/repo",
  "anthropic_api_key": "sk-ant-...",
  "check_interval_hours": 6,
  "repo_path": "/tmp/minbot-workspace"
}
```

**4. Authenticate GitHub CLI**

```bash
gh auth login
```

**5. Run**

```bash
uv run python -m minbot.bot
```

Open Telegram and send `/start` to your bot.

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show available commands |
| `/issues` | List open issues with difficulty/urgency estimates |
| `/suggest` | Get a recommendation on what to work on next |
| `/work <number>` | Have Claude Code work on an issue autonomously |
| `/status` | Check progress of current work |

## How `/work` works

When you send `/work 42`, minbot will:

1. Clone/pull the repo
2. Create a branch `issue-42`
3. Spawn Claude Code CLI with the issue context
4. Claude Code makes changes, commits, and pushes
5. minbot creates a PR and sends you the link

## Claude Code Authentication

The `/work` command requires [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude`) to be installed and authenticated.

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Authenticate (interactive, one-time)
claude

# Or set the API key directly (for non-interactive/Docker environments)
export ANTHROPIC_API_KEY="sk-ant-..."
```

In Docker, pass the API key as an environment variable. Claude Code prioritizes `ANTHROPIC_API_KEY` from the environment over interactive login.

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
  agent.py       # LLM reasoning (issue triage, suggestions)
  worker.py      # Claude Code subprocess for coding
  scheduler.py   # Periodic issue checking
  bot.py         # Telegram bot handlers (entry point)
```

## Line Count

```bash
bash core_lines.sh
```

```
minbot core line count
========================

  config.py              23 lines
  github.py              63 lines
  agent.py               57 lines
  worker.py              62 lines
  scheduler.py           51 lines
  bot.py                123 lines
  (root)                  3 lines

  Total:               382 lines
```
