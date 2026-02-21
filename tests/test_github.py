"""Tests for GitHub operations."""

import json
import subprocess
from unittest.mock import patch, MagicMock
from minbot import github


def _mock_run(stdout="", returncode=0):
    result = MagicMock()
    result.stdout = stdout
    result.returncode = returncode
    return result


@patch("subprocess.run")
def test_list_issues(mock_run):
    issues = [
        {"number": 1, "title": "Bug fix", "body": "Fix the bug", "labels": [], "createdAt": "2024-01-01", "comments": []},
        {"number": 2, "title": "Feature", "body": "Add feature", "labels": [], "createdAt": "2024-01-02", "comments": []},
    ]
    mock_run.return_value = _mock_run(stdout=json.dumps(issues))
    result = github.list_issues("owner/repo")
    assert len(result) == 2
    assert result[0]["number"] == 1
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "issue" in args
    assert "owner/repo" in args


@patch("subprocess.run")
def test_list_issues_empty(mock_run):
    mock_run.return_value = _mock_run(stdout="")
    result = github.list_issues("owner/repo")
    assert result == []


@patch("subprocess.run")
def test_get_issue(mock_run):
    issue = {"number": 1, "title": "Bug", "body": "Details", "labels": [], "comments": [], "createdAt": "2024-01-01"}
    mock_run.return_value = _mock_run(stdout=json.dumps(issue))
    result = github.get_issue("owner/repo", 1)
    assert result["number"] == 1
    assert result["title"] == "Bug"


@patch("subprocess.run")
def test_create_branch(mock_run):
    mock_run.return_value = _mock_run()
    github.create_branch("/tmp/repo", "feature-branch")
    args = mock_run.call_args[0][0]
    assert args == ["git", "checkout", "-b", "feature-branch"]
    assert mock_run.call_args[1]["cwd"] == "/tmp/repo"


@patch("subprocess.run")
def test_create_pr(mock_run):
    mock_run.return_value = _mock_run(stdout="https://github.com/owner/repo/pull/1")
    url = github.create_pr("owner/repo", "Title", "Body", "branch")
    assert "pull/1" in url


@patch("subprocess.run")
@patch("os.path.exists", return_value=True)
def test_clone_repo_pulls_if_exists(mock_exists, mock_run):
    mock_run.return_value = _mock_run()
    github.clone_repo("owner/repo", "/tmp/repo")
    args = mock_run.call_args[0][0]
    assert args == ["git", "pull"]


@patch("subprocess.run")
@patch("os.path.exists", return_value=False)
def test_clone_repo_clones_if_new(mock_exists, mock_run):
    mock_run.return_value = _mock_run()
    github.clone_repo("owner/repo", "/tmp/repo")
    args = mock_run.call_args[0][0]
    assert "clone" in args
