A minimal Telegram bot that helps manage GitHub development. It periodically checks repo issues, estimates difficulty/urgency, and suggests work. Users can also ask the bot to work on a specific issue.

Focused exclusively on coding development. Keep it lightweight.

## Quick start (local)

```
bash install.sh
```

This installs all prerequisites (`uv`, `gh`, `node`, `claude` CLI) if missing, then runs `uv sync`. After that:

```
uv run python -m minbot setup   # configure Telegram token, chat ID, repos
uv run minbot                   # start the bot
```

## Quick start (Docker)

```
docker compose up -d
```

## Prerequisites

- `gh` CLI (authenticated)
- `claude` CLI (for issue analysis when no Anthropic API key is configured)
- A Telegram bot token (create via @BotFather)

## Structure

- `minbot/config.py` - configuration and environment variables
- `minbot/github.py` - GitHub API client
- `minbot/agent.py` - Claude-based agent for issue analysis (SDK or CLI)
- `minbot/worker.py` - background worker for issue processing
- `minbot/scheduler.py` - periodic task scheduling and proactive suggestions
- `minbot/bot.py` - Telegram bot handlers
- `minbot/__main__.py` - entry point and setup

## Config

- `github_repos`: list of repos in `owner/repo` format
- `anthropic_api_key`: optional. If set, uses the Anthropic SDK. Otherwise, calls the `claude` CLI.
- `workspace_dir`: base directory for cloned repos (each repo cloned into `workspace_dir/<owner>/<repo>`)

## Guidelines

- Keep core agent code as short as possible.
- Design tests to verify functionality.
- Use `uv` for dependency management.
- Run tests with `pytest`.
