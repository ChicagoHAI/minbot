"""Claude Code CLI integration for working on issues and PRs."""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from minbot import github

log = logging.getLogger(__name__)

LOGS_DIR = os.path.join(str(Path.home()), ".minbot", "logs", "claude")


async def work_on_issue(
    workspace_dir: str, repo: str, issue: dict, on_output=None,
) -> str:
    """Run Claude Code on an issue. Returns the final output.

    Args:
        workspace_dir: Base directory for cloned repos.
        repo: GitHub repo in owner/repo format.
        issue: Issue dict with number, title, body.
        on_output: Optional async callback for streaming output lines.
    """
    repo_path = os.path.join(workspace_dir, repo)
    branch = f"issue-{issue['number']}"
    github.clone_repo(repo, repo_path)
    github.create_branch(repo_path, branch)

    prompt = (
        f"Work on this GitHub issue.\n\n"
        f"Issue #{issue['number']}: {issue['title']}\n\n"
        f"{issue.get('body', '')}\n\n"
        f"Steps:\n"
        f"1. Read the project's CLAUDE.md and .github/workflows/ to understand the full CI pipeline (build, test, lint, audit, etc.).\n"
        f"2. Make the changes to fix the issue.\n"
        f"3. Run every check from the CI pipeline. Fix all failures.\n"
        f"4. Merge the latest main: git fetch origin && git merge origin/main --no-edit\n"
        f"5. Run the build and tests again after the merge. Fix any issues.\n"
        f"6. Commit and push the branch '{branch}'."
    )

    # Log to file — no buffer limits, persistent for debugging
    log_dir = os.path.join(LOGS_DIR, repo.replace("/", "_"))
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"issue-{issue['number']}.log")

    cmd = [
        "claude", "--dangerously-skip-permissions",
        "-p", prompt,
    ]
    log.info("Running claude on %s#%s (log: %s)", repo, issue['number'], log_path)

    with open(log_path, "w") as log_file:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo_path,
            stdout=log_file,
            stderr=log_file,
        )
        await proc.wait()

    log.info("Claude finished with exit code %s (log: %s)", proc.returncode, log_path)

    with open(log_path) as f:
        output = f.read()

    if on_output and output:
        await on_output(output[-4000:])

    if proc.returncode != 0:
        return f"Claude Code exited with code {proc.returncode}\nLog: {log_path}\n{output[-2000:]}"

    # Push (Claude already merged main and ran tests)
    subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=repo_path, check=True, capture_output=True,
    )
    # Use the last portion of Claude's output as the PR summary
    summary = output.strip()[-3000:] if output.strip() else "No output captured."
    pr_body = (
        f"Closes #{issue['number']}\n\n"
        f"## Issue\n\n"
        f"**{issue['title']}**\n\n"
        f"{issue.get('body', '')[:500]}\n\n"
        f"## Changes\n\n"
        f"{summary}\n\n"
        f"---\n"
        f"Automated by [minbot](https://github.com/ChicagoHAI/minbot) using Claude Code."
    )
    pr_url = github.create_pr(
        repo,
        title=f"Fix #{issue['number']}: {issue['title']}",
        body=pr_body,
        branch=branch,
    )

    return f"Done! PR created: {pr_url}"


async def address_pr_comments(
    workspace_dir: str, repo: str, pr: dict, comments: list[dict],
    user_instructions: str = "", on_output=None,
) -> str:
    """Run Claude Code on a PR branch to address review comments.

    Args:
        workspace_dir: Base directory for cloned repos.
        repo: GitHub repo in owner/repo format.
        pr: PR dict with number, title, body, branch.
        comments: List of review/issue comments from get_pr_comments.
        user_instructions: Additional instructions from the user's Telegram message.
        on_output: Optional async callback for streaming output lines.
    """
    repo_path = os.path.join(workspace_dir, repo)
    branch = pr["branch"]
    github.clone_repo(repo, repo_path)
    github.checkout_pr_branch(repo_path, branch)

    comments_text = ""
    for c in comments:
        if c["type"] == "review":
            comments_text += f"- [{c['path']}:{c.get('line', '?')}] @{c['user']}: {c['body']}\n"
        else:
            comments_text += f"- @{c['user']}: {c['body']}\n"

    prompt = (
        f"Address the review comments on this pull request.\n\n"
        f"PR #{pr['number']}: {pr['title']}\n\n"
        f"{pr.get('body', '')}\n\n"
        f"Review comments to address:\n{comments_text}\n"
    )
    if user_instructions:
        prompt += f"\nAdditional instructions from the developer:\n{user_instructions}\n"

    prompt += (
        f"\nSteps:\n"
        f"1. Read the project's CLAUDE.md and .github/workflows/ to understand the full CI pipeline.\n"
        f"2. Address all review comments listed above.\n"
        f"3. Run every check from the CI pipeline. Fix all failures.\n"
        f"4. Commit and push to branch '{branch}'."
    )

    log_dir = os.path.join(LOGS_DIR, repo.replace("/", "_"))
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"pr-{pr['number']}.log")

    cmd = [
        "claude", "--dangerously-skip-permissions",
        "-p", prompt,
    ]
    log.info("Running claude on %s PR #%s (log: %s)", repo, pr['number'], log_path)

    with open(log_path, "w") as log_file:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo_path,
            stdout=log_file,
            stderr=log_file,
        )
        await proc.wait()

    log.info("Claude finished with exit code %s (log: %s)", proc.returncode, log_path)

    with open(log_path) as f:
        output = f.read()

    if on_output and output:
        await on_output(output[-4000:])

    if proc.returncode != 0:
        return f"Claude Code exited with code {proc.returncode}\nLog: {log_path}\n{output[-2000:]}"

    subprocess.run(
        ["git", "push", "origin", branch],
        cwd=repo_path, check=True, capture_output=True,
    )

    return f"Done! Pushed changes to branch '{branch}' for PR #{pr['number']}."
