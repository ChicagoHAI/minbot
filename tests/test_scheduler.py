"""Tests for scheduler issue checking."""

import json
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from minbot.scheduler import _check_issues
from minbot.config import Config


def _fake_config():
    return Config(
        telegram_token="fake-token",
        telegram_chat_id=12345,
        github_token="ghp_fake",
        github_repos=["owner/repo"],
    )


@pytest.mark.asyncio
@patch("minbot.scheduler._save_known_issues")
@patch("minbot.scheduler._load_known_issues")
@patch("minbot.scheduler.agent")
@patch("minbot.scheduler.github")
async def test_check_issues_detects_new_after_empty(mock_gh, mock_agent, mock_load, mock_save):
    """After a first check with 0 issues, new issues should be detected."""
    send = AsyncMock()
    config = _fake_config()

    # First check: no issues. Simulates known_issues saved as empty set.
    mock_load.return_value = {"owner/repo": set()}
    mock_gh.list_issues.return_value = [
        {"number": 1, "title": "New bug", "body": ""},
    ]
    mock_agent.analyze_issues.return_value = [
        {"number": 1, "title": "New bug", "difficulty": "easy", "urgency": "high", "summary": "Fix it"},
    ]

    await _check_issues(config, send)

    # Should have notified about the new issue
    texts = [call[0][0] for call in send.call_args_list]
    assert any("New issues" in t and "#1" in t for t in texts)


@pytest.mark.asyncio
@patch("minbot.scheduler._save_known_issues")
@patch("minbot.scheduler._load_known_issues")
@patch("minbot.scheduler.github")
async def test_check_issues_first_run_no_notification(mock_gh, mock_load, mock_save):
    """First run (no known issues file) should not notify about existing issues."""
    send = AsyncMock()
    config = _fake_config()

    mock_load.return_value = {}
    mock_gh.list_issues.return_value = [
        {"number": 1, "title": "Existing issue", "body": ""},
    ]

    await _check_issues(config, send)

    texts = [call[0][0] for call in send.call_args_list]
    assert not any("New issues" in t for t in texts)


@pytest.mark.asyncio
@patch("minbot.scheduler._save_known_issues")
@patch("minbot.scheduler._load_known_issues")
@patch("minbot.scheduler.github")
async def test_check_issues_all_empty(mock_gh, mock_load, mock_save):
    """When there are no issues at all, should report no new issues."""
    send = AsyncMock()
    config = _fake_config()

    mock_load.return_value = {}
    mock_gh.list_issues.return_value = []

    await _check_issues(config, send)

    texts = [call[0][0] for call in send.call_args_list]
    assert any("no new issues" in t for t in texts)
