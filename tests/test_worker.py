"""Tests for Claude Code worker."""

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
import pytest
from minbot import worker


@pytest.mark.asyncio
@patch("minbot.worker.github")
@patch("asyncio.create_subprocess_exec")
async def test_work_on_issue_success(mock_exec, mock_gh):
    proc = AsyncMock()
    proc.returncode = 0
    proc.wait = AsyncMock()
    mock_exec.return_value = proc

    mock_gh.clone_repo = MagicMock()
    mock_gh.create_branch = MagicMock()
    mock_gh.create_pr = MagicMock(return_value="https://github.com/owner/repo/pull/1")

    log_content = "Analyzing issue...\nMaking changes...\nDone.\n"
    m = mock_open(read_data=log_content)

    with patch("subprocess.run"), patch("builtins.open", m), patch("os.makedirs"):
        issue = {"number": 1, "title": "Fix bug", "body": "Details"}
        result = await worker.work_on_issue("/workspace", "owner/repo", issue)

    assert "PR created" in result
    mock_gh.create_branch.assert_called_once_with("/workspace/owner/repo", "issue-1")


@pytest.mark.asyncio
@patch("minbot.worker.github")
@patch("asyncio.create_subprocess_exec")
async def test_work_on_issue_failure(mock_exec, mock_gh):
    proc = AsyncMock()
    proc.returncode = 1
    proc.wait = AsyncMock()
    mock_exec.return_value = proc

    mock_gh.clone_repo = MagicMock()
    mock_gh.create_branch = MagicMock()

    log_content = "Error occurred\n"
    m = mock_open(read_data=log_content)

    with patch("builtins.open", m), patch("os.makedirs"):
        issue = {"number": 1, "title": "Fix bug", "body": "Details"}
        result = await worker.work_on_issue("/workspace", "owner/repo", issue)

    assert "exited with code 1" in result


@pytest.mark.asyncio
@patch("minbot.worker.github")
@patch("asyncio.create_subprocess_exec")
async def test_work_on_issue_calls_on_output(mock_exec, mock_gh):
    proc = AsyncMock()
    proc.returncode = 0
    proc.wait = AsyncMock()
    mock_exec.return_value = proc

    mock_gh.clone_repo = MagicMock()
    mock_gh.create_branch = MagicMock()
    mock_gh.create_pr = MagicMock(return_value="https://github.com/owner/repo/pull/1")

    collected = []

    async def on_output(text):
        collected.append(text)

    log_content = "line1\nline2\n"
    m = mock_open(read_data=log_content)

    with patch("subprocess.run"), patch("builtins.open", m), patch("os.makedirs"):
        issue = {"number": 5, "title": "Add feature", "body": ""}
        await worker.work_on_issue("/workspace", "owner/repo", issue, on_output)

    assert len(collected) == 1
    assert "line1" in collected[0]
    assert "line2" in collected[0]
