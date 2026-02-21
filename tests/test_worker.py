"""Tests for Claude Code worker."""

import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from minbot import worker


@pytest.mark.asyncio
@patch("minbot.worker.github")
@patch("asyncio.create_subprocess_exec")
async def test_work_on_issue_success(mock_exec, mock_gh):
    proc = AsyncMock()
    proc.returncode = 0
    proc.wait = AsyncMock()

    async def mock_lines():
        for line in [b"Analyzing issue...\n", b"Making changes...\n", b"Done.\n"]:
            yield line

    proc.stdout = mock_lines()
    mock_exec.return_value = proc

    mock_gh.clone_repo = MagicMock()
    mock_gh.create_branch = MagicMock()
    mock_gh.create_pr = MagicMock(return_value="https://github.com/owner/repo/pull/1")

    with patch("subprocess.run"):
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

    async def mock_lines():
        for line in [b"Error occurred\n"]:
            yield line

    proc.stdout = mock_lines()
    mock_exec.return_value = proc

    mock_gh.clone_repo = MagicMock()
    mock_gh.create_branch = MagicMock()

    issue = {"number": 1, "title": "Fix bug", "body": "Details"}
    result = await worker.work_on_issue("/workspace", "owner/repo", issue)

    assert "exited with code 1" in result


@pytest.mark.asyncio
@patch("minbot.worker.github")
@patch("asyncio.create_subprocess_exec")
async def test_work_on_issue_streams_output(mock_exec, mock_gh):
    proc = AsyncMock()
    proc.returncode = 0
    proc.wait = AsyncMock()

    async def mock_lines():
        for line in [b"line1\n", b"line2\n"]:
            yield line

    proc.stdout = mock_lines()
    mock_exec.return_value = proc

    mock_gh.clone_repo = MagicMock()
    mock_gh.create_branch = MagicMock()
    mock_gh.create_pr = MagicMock(return_value="https://github.com/owner/repo/pull/1")

    collected = []

    async def on_output(text):
        collected.append(text)

    with patch("subprocess.run"):
        issue = {"number": 5, "title": "Add feature", "body": ""}
        await worker.work_on_issue("/workspace", "owner/repo", issue, on_output)

    assert collected == ["line1", "line2"]
