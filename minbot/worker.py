"""Claude Code CLI integration for working on issues."""

import asyncio
import logging
import os
import subprocess
from minbot import github

log = logging.getLogger(__name__)

LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs", "claude")


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
    pr_url = github.create_pr(
        repo,
        title=f"Fix #{issue['number']}: {issue['title']}",
        body=f"Closes #{issue['number']}\n\nAutomated by minbot using Claude Code.",
        branch=branch,
    )

    return f"Done! PR created: {pr_url}"
