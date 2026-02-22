"""GitHub operations via PyGithub + git CLI."""

import os
import subprocess
from github import Github

_client: Github | None = None
_token: str | None = None


def set_token(token: str) -> None:
    """Set the GitHub token used for API and git operations."""
    global _client, _token
    _token = token
    _client = Github(token)


def _get_repo(repo: str):
    return _client.get_repo(repo)


def list_issues(repo: str) -> list[dict]:
    """List open issues for a repo."""
    issues = _get_repo(repo).get_issues(state="open")
    return [
        {
            "number": i.number,
            "title": i.title,
            "body": i.body or "",
            "labels": [l.name for l in i.labels],
            "createdAt": i.created_at.isoformat(),
        }
        for i in issues[:30]
    ]


def get_issue(repo: str, number: int) -> dict:
    """Get a single issue with full details."""
    i = _get_repo(repo).get_issue(number)
    return {
        "number": i.number,
        "title": i.title,
        "body": i.body or "",
        "labels": [l.name for l in i.labels],
        "createdAt": i.created_at.isoformat(),
    }


def create_branch(repo_path: str, name: str) -> None:
    """Create and checkout a branch. Switch to it if it already exists."""
    result = subprocess.run(
        ["git", "checkout", "-b", name],
        cwd=repo_path, capture_output=True,
    )
    if result.returncode != 0:
        subprocess.run(
            ["git", "checkout", name],
            cwd=repo_path, check=True, capture_output=True,
        )


def create_pr(repo: str, title: str, body: str, branch: str) -> str:
    """Create a pull request, return the URL."""
    r = _get_repo(repo)
    pr = r.create_pull(title=title, body=body, head=branch, base=r.default_branch)
    return pr.html_url


def clone_repo(repo: str, path: str) -> None:
    """Clone a repo (or pull if already cloned)."""
    if os.path.exists(os.path.join(path, ".git")):
        subprocess.run(
            ["git", "pull"], cwd=path, check=True, capture_output=True,
        )
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        subprocess.run(
            ["git", "clone", f"https://x-access-token:{_token}@github.com/{repo}.git", path],
            check=True, capture_output=True,
        )
