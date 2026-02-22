"""Claude Code CLI integration for working on issues."""

import asyncio
import logging
import os
import subprocess
from minbot import github

log = logging.getLogger(__name__)


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
        f"Make the changes, commit them, and push the branch '{branch}'."
    )

    proc = await asyncio.create_subprocess_exec(
        "claude", "--print", "--dangerously-skip-permissions",
        "-p", prompt,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    lines = []
    async for line in proc.stdout:
        text = line.decode().rstrip()
        lines.append(text)
        log.info("[claude] %s", text)
        if on_output:
            await on_output(text)

    await proc.wait()

    if proc.returncode != 0:
        return f"Claude Code exited with code {proc.returncode}\n" + "\n".join(lines[-20:])

    # Push and create PR
    subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=repo_path, check=True, capture_output=True,
    )
    pr_url = github.create_pr(
        repo,
        title=f"Fix #{issue['number']}: {issue['title']}",
        body=f"Closes #{issue['number']}\n\nAutomated by minbot using Claude Code.",
        branch=branch,
    )

    return f"Done! PR created: {pr_url}"
