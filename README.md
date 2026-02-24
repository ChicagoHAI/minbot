<p align="center">
  <img src="https://chicagohai.github.io/avatar.jpg" width="120" alt="minbot" />
</p>

<h1 align="center">minbot: Minimal Telegram Bot for GitHub Development</h1>

<p align="center">
  <a href="https://github.com/ChicagoHAI/minbot"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python" /></a>
  <a href="https://github.com/ChicagoHAI/minbot/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License" /></a>
</p>

A lightweight Telegram bot that monitors GitHub issues, estimates difficulty/urgency, suggests what to work on, and can autonomously work on issues using Claude Code.

<!-- BEGIN LINE COUNT -->
📏 Core bot in **627 lines** of Python (run `bash core_lines.sh` to verify)
<!-- END LINE COUNT -->

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

This builds the image (installs Python deps, Claude CLI) and starts the bot. Your config is mounted into the container automatically.

Open Telegram and send `/start` to your bot. The first user to `/start` claims the bot — their chat ID is saved and all commands from other users are ignored.

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
| `/issues [repo]` | List open issues with difficulty/urgency estimates |
| `/suggest [repo]` | Get a recommendation on what to work on next |
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

## Configuration

All config lives in `~/.minbot/`. The full set of options in `config.json`:

| Key | Default | Description |
|-----|---------|-------------|
| `telegram_token` | (required) | Telegram bot token |
| `github_token` | (required) | GitHub token with `repo` scope |
| `github_repos` | (required) | List of repos in `owner/repo` format |
| `anthropic_api_key` | `null` | If set, uses Anthropic SDK instead of Claude CLI |
| `check_interval_hours` | `6` | How often to check for new issues |
| `suggest_interval_hours` | `24` | How often to send work suggestions |
| `workspace_dir` | `"/workspace"` | Where repos are cloned |

### Environment variables for `/work`

When Claude works on an issue, it may need API keys to run tests or experiments. Create `~/.minbot/.env` with any variables your projects need:

```
OPENROUTER_API_KEY=sk-or-...
DATABASE_URL=postgres://...
```

These are automatically loaded into the Docker container and available to the Claude worker process.

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

