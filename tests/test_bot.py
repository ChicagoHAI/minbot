"""Tests for Telegram bot command handlers."""

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from minbot.bot import cmd_start, cmd_issues, cmd_status, cmd_work, cmd_suggest
from minbot.config import Config


def _make_update():
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


def _make_context(args=None):
    ctx = MagicMock()
    ctx.args = args or []
    return ctx


def _fake_config():
    return Config(
        telegram_token="fake-token",
        telegram_chat_id=12345,
        github_repo="owner/repo",
        anthropic_api_key="fake-key",
    )


@pytest.mark.asyncio
async def test_cmd_start():
    update = _make_update()
    await cmd_start(update, _make_context())
    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args[0][0]
    assert "/issues" in text
    assert "/work" in text


@pytest.mark.asyncio
@patch("minbot.bot._get_config")
@patch("minbot.bot.agent")
@patch("minbot.bot.github")
async def test_cmd_issues(mock_gh, mock_agent, mock_config):
    mock_config.return_value = _fake_config()
    mock_gh.list_issues.return_value = [
        {"number": 1, "title": "Bug", "body": "Fix"},
    ]
    mock_agent.analyze_issues.return_value = [
        {"number": 1, "title": "Bug", "difficulty": "easy", "urgency": "high", "summary": "Fix the bug"},
    ]

    update = _make_update()
    await cmd_issues(update, _make_context())

    # Two calls: "Fetching issues..." and the result
    assert update.message.reply_text.call_count == 2
    text = update.message.reply_text.call_args[0][0]
    assert "#1" in text
    assert "easy" in text


@pytest.mark.asyncio
@patch("minbot.bot._get_config")
@patch("minbot.bot.agent")
@patch("minbot.bot.github")
async def test_cmd_issues_empty(mock_gh, mock_agent, mock_config):
    mock_config.return_value = _fake_config()
    mock_gh.list_issues.return_value = []

    update = _make_update()
    await cmd_issues(update, _make_context())

    texts = [call[0][0] for call in update.message.reply_text.call_args_list]
    assert any("No open issues" in t for t in texts)


@pytest.mark.asyncio
async def test_cmd_status_no_work():
    update = _make_update()
    await cmd_status(update, _make_context())
    text = update.message.reply_text.call_args[0][0]
    assert "No work" in text


@pytest.mark.asyncio
async def test_cmd_work_no_args():
    update = _make_update()
    await cmd_work(update, _make_context(args=[]))
    text = update.message.reply_text.call_args[0][0]
    assert "Usage" in text


@pytest.mark.asyncio
@patch("minbot.bot._get_config")
@patch("minbot.bot.agent")
@patch("minbot.bot.github")
async def test_cmd_suggest(mock_gh, mock_agent, mock_config):
    mock_config.return_value = _fake_config()
    mock_gh.list_issues.return_value = [{"number": 1, "title": "Bug"}]
    mock_agent.analyze_issues.return_value = [{"number": 1, "difficulty": "easy", "urgency": "high"}]
    mock_agent.suggest_next.return_value = "Work on #1."

    update = _make_update()
    await cmd_suggest(update, _make_context())

    text = update.message.reply_text.call_args[0][0]
    assert "#1" in text
