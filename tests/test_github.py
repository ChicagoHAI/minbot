"""Tests for GitHub operations."""

from unittest.mock import patch, MagicMock
from minbot import github


def _setup_client():
    """Set up a mock GitHub client."""
    mock_client = MagicMock()
    github._client = mock_client
    github._token = "fake-token"
    return mock_client


def _mock_issue(number=1, title="Bug", body="Details", labels=None):
    issue = MagicMock()
    issue.number = number
    issue.title = title
    issue.body = body
    issue.labels = [MagicMock(name=l) for l in (labels or [])]
    issue.created_at = MagicMock(isoformat=MagicMock(return_value="2024-01-01T00:00:00"))
    return issue


def test_list_issues():
    client = _setup_client()
    repo = client.get_repo.return_value
    repo.get_issues.return_value = [
        _mock_issue(1, "Bug fix", "Fix the bug"),
        _mock_issue(2, "Feature", "Add feature"),
    ]
    result = github.list_issues("owner/repo")
    assert len(result) == 2
    assert result[0]["number"] == 1
    assert result[1]["title"] == "Feature"
    client.get_repo.assert_called_once_with("owner/repo")


def test_list_issues_empty():
    client = _setup_client()
    repo = client.get_repo.return_value
    repo.get_issues.return_value = []
    result = github.list_issues("owner/repo")
    assert result == []


def test_get_issue():
    client = _setup_client()
    repo = client.get_repo.return_value
    repo.get_issue.return_value = _mock_issue(1, "Bug", "Details")
    result = github.get_issue("owner/repo", 1)
    assert result["number"] == 1
    assert result["title"] == "Bug"
    repo.get_issue.assert_called_once_with(1)


@patch("subprocess.run")
def test_create_branch(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    github.create_branch("/tmp/repo", "feature-branch")
    args = mock_run.call_args[0][0]
    assert args == ["git", "checkout", "-b", "feature-branch"]
    assert mock_run.call_args[1]["cwd"] == "/tmp/repo"


def test_create_pr():
    client = _setup_client()
    repo = client.get_repo.return_value
    repo.default_branch = "main"
    pr = MagicMock()
    pr.html_url = "https://github.com/owner/repo/pull/1"
    repo.create_pull.return_value = pr
    url = github.create_pr("owner/repo", "Title", "Body", "branch")
    assert "pull/1" in url
    repo.create_pull.assert_called_once_with(
        title="Title", body="Body", head="branch", base="main",
    )


@patch("subprocess.run")
@patch("os.path.exists", return_value=True)
def test_clone_repo_pulls_if_exists(mock_exists, mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    github.clone_repo("owner/repo", "/tmp/repo")
    args = mock_run.call_args[0][0]
    assert args == ["git", "pull"]


@patch("subprocess.run")
@patch("os.path.exists", return_value=False)
def test_clone_repo_clones_if_new(mock_exists, mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    github.clone_repo("owner/repo", "/tmp/repo")
    args = mock_run.call_args[0][0]
    assert "clone" in args
