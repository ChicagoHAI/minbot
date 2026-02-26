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


def list_issues(repo: str, include_prs: bool = False) -> list[dict]:
    """List open issues for a repo. Optionally include pull requests."""
    results = []
    for i in _get_repo(repo).get_issues(state="open"):
        if not include_prs and i.pull_request is not None:
            continue
        results.append({
            "number": i.number,
            "title": i.title,
            "body": i.body or "",
            "labels": [l.name for l in i.labels],
            "createdAt": i.created_at.isoformat(),
            "is_pr": i.pull_request is not None,
        })
        if len(results) >= 30:
            break
    return results


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
    """Create and checkout a branch, or switch to it and merge main."""
    result = subprocess.run(
        ["git", "checkout", "-b", name],
        cwd=repo_path, capture_output=True,
    )
    if result.returncode != 0:
        subprocess.run(
            ["git", "checkout", name],
            cwd=repo_path, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "merge", "origin/main", "--no-edit"],
            cwd=repo_path, check=True, capture_output=True,
        )


def create_pr(repo: str, title: str, body: str, branch: str) -> str:
    """Create a pull request or return the existing one's URL."""
    r = _get_repo(repo)
    # Check for existing PR on this branch
    existing = r.get_pulls(state="open", head=f"{r.owner.login}:{branch}")
    for pr in existing:
        return pr.html_url
    pr = r.create_pull(title=title, body=body, head=branch, base=r.default_branch)
    return pr.html_url


def list_prs(repo: str) -> list[dict]:
    """List open pull requests for a repo."""
    results = []
    for pr in _get_repo(repo).get_pulls(state="open"):
        results.append({
            "number": pr.number,
            "title": pr.title,
            "body": pr.body or "",
            "branch": pr.head.ref,
        })
        if len(results) >= 20:
            break
    return results


def get_pr(repo: str, number: int) -> dict:
    """Fetch PR details (title, body, branch name)."""
    pr = _get_repo(repo).get_pull(number)
    return {
        "number": pr.number,
        "title": pr.title,
        "body": pr.body or "",
        "branch": pr.head.ref,
        "base": pr.base.ref,
    }


def get_pr_comments(repo: str, number: int) -> list[dict]:
    """Fetch review comments (line-level) and issue comments for a PR."""
    r = _get_repo(repo)
    pr = r.get_pull(number)
    comments = []
    # Line-level review comments
    for c in pr.get_review_comments():
        comments.append({
            "type": "review",
            "path": c.path,
            "line": c.position,
            "body": c.body,
            "user": c.user.login,
        })
    # General issue comments on the PR
    for c in pr.get_issue_comments():
        comments.append({
            "type": "issue",
            "body": c.body,
            "user": c.user.login,
        })
    return comments


def checkout_pr_branch(repo_path: str, branch: str) -> None:
    """Fetch and checkout an existing PR branch."""
    subprocess.run(
        ["git", "fetch", "origin", branch],
        cwd=repo_path, check=True, capture_output=True,
    )
    result = subprocess.run(
        ["git", "checkout", branch],
        cwd=repo_path, capture_output=True,
    )
    if result.returncode != 0:
        subprocess.run(
            ["git", "checkout", "-b", branch, f"origin/{branch}"],
            cwd=repo_path, check=True, capture_output=True,
        )
    else:
        subprocess.run(
            ["git", "pull", "origin", branch],
            cwd=repo_path, check=True, capture_output=True,
        )


def create_issue(repo: str, title: str, body: str) -> str:
    """Create a GitHub issue. Returns the issue URL."""
    issue = _get_repo(repo).create_issue(title=title, body=body)
    return issue.html_url


def add_pr_comment(repo: str, number: int, body: str) -> None:
    """Add a general comment on a PR."""
    _get_repo(repo).get_issue(number).create_comment(body)


def clone_repo(repo: str, path: str) -> None:
    """Clone a repo, or if already cloned, checkout main and pull."""
    if os.path.exists(os.path.join(path, ".git")):
        # Get default branch name
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "--short"],
            cwd=path, capture_output=True, text=True,
        )
        main_branch = result.stdout.strip().removeprefix("origin/") if result.returncode == 0 else "main"
        subprocess.run(
            ["git", "checkout", main_branch],
            cwd=path, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "pull"], cwd=path, check=True, capture_output=True,
        )
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        subprocess.run(
            ["git", "clone", f"https://x-access-token:{_token}@github.com/{repo}.git", path],
            check=True, capture_output=True,
        )
