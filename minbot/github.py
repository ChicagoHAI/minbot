"""GitHub operations via `gh` CLI."""

import json
import subprocess


def _run(args: list[str]) -> str:
    result = subprocess.run(
        ["gh"] + args, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def list_issues(repo: str) -> list[dict]:
    """List open issues for a repo."""
    out = _run([
        "issue", "list", "--repo", repo,
        "--state", "open", "--json",
        "number,title,body,labels,createdAt,comments",
        "--limit", "30",
    ])
    return json.loads(out) if out else []


def get_issue(repo: str, number: int) -> dict:
    """Get a single issue with full details."""
    out = _run([
        "issue", "view", str(number), "--repo", repo,
        "--json", "number,title,body,labels,comments,createdAt",
    ])
    return json.loads(out)


def create_branch(repo_path: str, name: str) -> None:
    """Create and checkout a new branch."""
    subprocess.run(
        ["git", "checkout", "-b", name],
        cwd=repo_path, check=True, capture_output=True,
    )


def create_pr(repo: str, title: str, body: str, branch: str) -> str:
    """Create a pull request, return the URL."""
    out = _run([
        "pr", "create", "--repo", repo,
        "--title", title, "--body", body,
        "--head", branch,
    ])
    return out


def clone_repo(repo: str, path: str) -> None:
    """Clone a repo (or pull if already cloned)."""
    import os
    if os.path.exists(os.path.join(path, ".git")):
        subprocess.run(
            ["git", "pull"], cwd=path, check=True, capture_output=True,
        )
    else:
        subprocess.run(
            ["gh", "repo", "clone", repo, path],
            check=True, capture_output=True,
        )
