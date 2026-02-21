"""Tests for LLM agent reasoning."""

import json
from unittest.mock import patch, MagicMock
from minbot import agent


def _mock_message(text: str):
    msg = MagicMock()
    block = MagicMock()
    block.text = text
    msg.content = [block]
    return msg


@patch("minbot.agent.anthropic")
def test_analyze_issues_sdk(mock_anthropic):
    client = MagicMock()
    mock_anthropic.Anthropic.return_value = client

    analysis = [
        {"number": 1, "title": "Bug", "difficulty": "easy", "urgency": "high", "summary": "Fix the bug"},
        {"number": 2, "title": "Feature", "difficulty": "hard", "urgency": "low", "summary": "Add feature"},
    ]
    client.messages.create.return_value = _mock_message(json.dumps(analysis))

    issues = [
        {"number": 1, "title": "Bug", "body": "Fix it"},
        {"number": 2, "title": "Feature", "body": "Add it"},
    ]
    result = agent.analyze_issues(issues, api_key="fake-key")
    assert len(result) == 2
    assert result[0]["difficulty"] == "easy"
    assert result[1]["urgency"] == "low"
    client.messages.create.assert_called_once()


@patch("minbot.agent.subprocess")
def test_analyze_issues_cli(mock_subprocess):
    analysis = [
        {"number": 1, "title": "Bug", "difficulty": "easy", "urgency": "high", "summary": "Fix the bug"},
    ]
    mock_subprocess.run.return_value = MagicMock(
        stdout=json.dumps(analysis), returncode=0,
    )

    issues = [{"number": 1, "title": "Bug", "body": "Fix it"}]
    result = agent.analyze_issues(issues)
    assert len(result) == 1
    assert result[0]["difficulty"] == "easy"
    mock_subprocess.run.assert_called_once()


def test_analyze_issues_empty():
    result = agent.analyze_issues([])
    assert result == []


@patch("minbot.agent.anthropic")
def test_suggest_next_sdk(mock_anthropic):
    client = MagicMock()
    mock_anthropic.Anthropic.return_value = client
    client.messages.create.return_value = _mock_message("Work on issue #1 first because it's urgent.")

    issues = [{"number": 1, "title": "Bug", "difficulty": "easy", "urgency": "high"}]
    result = agent.suggest_next(issues, api_key="fake-key")
    assert "#1" in result


@patch("minbot.agent.subprocess")
def test_suggest_next_cli(mock_subprocess):
    mock_subprocess.run.return_value = MagicMock(
        stdout="Work on issue #1 first.", returncode=0,
    )

    issues = [{"number": 1, "title": "Bug", "difficulty": "easy", "urgency": "high"}]
    result = agent.suggest_next(issues)
    assert "#1" in result


def test_suggest_next_empty():
    result = agent.suggest_next([])
    assert "No open issues" in result
