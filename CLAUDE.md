A minimal Telegram bot that helps manage GitHub development. It takes a GitHub token to onboard, runs in Docker, periodically checks repo issues, estimates difficulty/urgency, and suggests work. Users can also ask the bot to work on a specific issue.

Focused exclusively on coding development. Keep it lightweight.

## Structure

- `minbot/config.py` - configuration and environment variables
- `minbot/github.py` - GitHub API client
- `minbot/agent.py` - Claude-based agent for issue analysis
- `minbot/worker.py` - background worker for issue processing
- `minbot/scheduler.py` - periodic task scheduling
- `minbot/bot.py` - Telegram bot handlers
- `minbot/__main__.py` - entry point

## Guidelines

- Keep core agent code as short as possible.
- Design tests to verify functionality.
- Use `uv` for dependency management.
- Run tests with `pytest`.