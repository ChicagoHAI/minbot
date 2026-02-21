"""GitHub operations via `gh` CLI."""

import json
import os
import subprocess

_token: str | None = None


def set_token(token: str) -> None:
    """Set the GitHub token used for all gh/git operations."""
    global _token
    _token = token


def _env() -> dict[str, str]:
    """Return environment with GH_TOKEN set."""
    env = os.environ.copy()
    if _token:
        env["GH_TOKEN"] = _token
    return env


def _run(args: list[str]) -> str:
    result = subprocess.run(
        ["gh"] + args, capture_output=True, text=True, check=True, env=_env(),
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
    if os.path.exists(os.path.join(path, ".git")):
        subprocess.run(
            ["git", "pull"], cwd=path, check=True, capture_output=True,
        )
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        subprocess.run(
            ["git", "clone", f"git@github.com:{repo}.git", path],
            check=True, capture_output=True,
        )
