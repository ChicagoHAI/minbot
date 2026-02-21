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


@patch("anthropic.Anthropic")
def test_analyze_issues(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client

    analysis = [
        {"number": 1, "title": "Bug", "difficulty": "easy", "urgency": "high", "summary": "Fix the bug"},
        {"number": 2, "title": "Feature", "difficulty": "hard", "urgency": "low", "summary": "Add feature"},
    ]
    client.messages.create.return_value = _mock_message(json.dumps(analysis))

    issues = [
        {"number": 1, "title": "Bug", "body": "Fix it"},
        {"number": 2, "title": "Feature", "body": "Add it"},
    ]
    result = agent.analyze_issues("fake-key", issues)
    assert len(result) == 2
    assert result[0]["difficulty"] == "easy"
    assert result[1]["urgency"] == "low"
    client.messages.create.assert_called_once()


def test_analyze_issues_empty():
    result = agent.analyze_issues("fake-key", [])
    assert result == []


@patch("anthropic.Anthropic")
def test_suggest_next(mock_cls):
    client = MagicMock()
    mock_cls.return_value = client
    client.messages.create.return_value = _mock_message("Work on issue #1 first because it's urgent.")

    issues = [{"number": 1, "title": "Bug", "difficulty": "easy", "urgency": "high"}]
    result = agent.suggest_next("fake-key", issues)
    assert "#1" in result


def test_suggest_next_empty():
    result = agent.suggest_next("fake-key", [])
    assert "No open issues" in result
