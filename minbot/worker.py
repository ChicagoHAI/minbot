"""Claude Code CLI integration for working on issues and PRs."""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from minbot import github

log = logging.getLogger(__name__)

LOGS_DIR = os.path.join(str(Path.home()), ".minbot", "logs", "claude")


def _format_comments(comments: list[dict]) -> str:
    """Format PR comments into readable text for prompts."""
    lines = []
    for c in comments:
        if c["type"] == "review":
            lines.append(f"- [{c['path']}:{c.get('line', '?')}] @{c['user']}: {c['body']}")
        else:
            lines.append(f"- @{c['user']}: {c['body']}")
    return "\n".join(lines)


async def _run_claude(repo_path: str, prompt: str, log_path: str, on_output=None) -> tuple[int, str]:
    """Run Claude Code CLI and return (exit_code, output).

    Handles logging, subprocess management, and output capture.
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    cmd = ["claude", "--dangerously-skip-permissions", "-p", prompt]
    log.info("Running claude (log: %s)", log_path)

    with open(log_path, "w") as log_file:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=repo_path, stdout=log_file, stderr=log_file,
        )
        await proc.wait()

    log.info("Claude finished with exit code %s (log: %s)", proc.returncode, log_path)

    with open(log_path) as f:
        output = f.read()

    if on_output and output:
        await on_output(output[-4000:])

    return proc.returncode, output


def _log_path_for(repo: str, name: str) -> str:
    return os.path.join(LOGS_DIR, repo.replace("/", "_"), name)


async def work_on_issue(
    workspace_dir: str, repo: str, issue: dict, on_output=None,
) -> str:
    """Run Claude Code on an issue. Returns the final output."""
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

    rc, output = await _run_claude(
        repo_path, prompt,
        _log_path_for(repo, f"issue-{issue['number']}.log"),
        on_output,
    )
    if rc != 0:
        return f"Claude Code exited with code {rc}\n{output[-2000:]}"

    subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=repo_path, check=True, capture_output=True,
    )
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
    """Run Claude Code on a PR branch to address review comments."""
    repo_path = os.path.join(workspace_dir, repo)
    branch = pr["branch"]
    github.clone_repo(repo, repo_path)
    github.checkout_pr_branch(repo_path, branch)

    comments_text = _format_comments(comments)
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

    rc, output = await _run_claude(
        repo_path, prompt,
        _log_path_for(repo, f"pr-{pr['number']}.log"),
        on_output,
    )
    if rc != 0:
        return f"Claude Code exited with code {rc}\n{output[-2000:]}"

    subprocess.run(
        ["git", "push", "origin", branch],
        cwd=repo_path, check=True, capture_output=True,
    )
    return f"Done! Pushed changes to branch '{branch}' for PR #{pr['number']}."


async def review_and_improve_pr(
    workspace_dir: str, repo: str, pr: dict, comments: list[dict],
    on_output=None,
) -> str:
    """Review a PR's code, address existing comments, and improve the code.

    Unlike address_pr_comments (which only addresses existing review comments),
    this also reviews the PR code itself and fixes any issues it finds.
    """
    repo_path = os.path.join(workspace_dir, repo)
    branch = pr["branch"]
    github.clone_repo(repo, repo_path)
    github.checkout_pr_branch(repo_path, branch)

    comments_text = _format_comments(comments)
    comments_section = f"Existing review comments to address:\n{comments_text}\n" if comments_text else ""

    prompt = (
        f"Review and improve this pull request.\n\n"
        f"PR #{pr['number']}: {pr['title']}\n\n"
        f"{pr.get('body', '')}\n\n"
        f"{comments_section}"
        f"Steps:\n"
        f"1. Read the project's CLAUDE.md and .github/workflows/ to understand the full CI pipeline.\n"
        f"2. Review the code changes in this PR branch. Look for:\n"
        f"   - Bugs, logic errors, or edge cases\n"
        f"   - Code quality issues (readability, maintainability)\n"
        f"   - Performance problems\n"
        f"   - Missing error handling at system boundaries\n"
        f"3. Address all existing review comments listed above (if any).\n"
        f"4. Fix any issues you identified in step 2.\n"
        f"5. Run every check from the CI pipeline. Fix all failures.\n"
        f"6. Commit and push to branch '{branch}'."
    )

    rc, output = await _run_claude(
        repo_path, prompt,
        _log_path_for(repo, f"pr-review-{pr['number']}.log"),
        on_output,
    )
    if rc != 0:
        return f"Claude Code exited with code {rc}\n{output[-2000:]}"

    subprocess.run(
        ["git", "push", "origin", branch],
        cwd=repo_path, check=True, capture_output=True,
    )
    return output.strip()[-3000:] if output.strip() else "No output captured."
