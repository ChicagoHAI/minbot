"""LLM reasoning for issue triage and suggestions."""

import json
import logging
import subprocess

log = logging.getLogger(__name__)

try:
    import anthropic
except ImportError:
    anthropic = None

SYSTEM = """You are a software development triage assistant. You analyze GitHub issues and estimate their difficulty and urgency.

Respond in JSON only. No markdown fences."""


def _call_cli(prompt: str, system: str | None = None) -> str:
    """Call claude CLI as a subprocess."""
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    result = subprocess.run(
        ["claude", "--print", "-p", full_prompt],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed (exit {result.returncode}): {result.stderr.strip()}")
    output = result.stdout.strip()
    if not output:
        raise RuntimeError(f"claude CLI returned empty output. stderr: {result.stderr.strip()}")
    return output


def _call(prompt: str, api_key: str | None = None, system: str | None = None) -> str:
    if api_key and anthropic:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    return _call_cli(prompt, system)


def analyze_issues(issues: list[dict], api_key: str | None = None, prs: list[dict] | None = None) -> list[dict]:
    """Estimate difficulty and urgency for each issue.

    Returns list of {number, title, difficulty, urgency, summary, has_pr}.
    """
    if not issues:
        return []
    pr_section = ""
    if prs:
        pr_section = f"\n\nOpen pull requests (issues with PRs are already being worked on):\n{json.dumps(prs, indent=2, default=str)}\n"

    prompt = f"""Analyze these GitHub issues. For each, estimate:
- difficulty: easy / medium / hard
- urgency: low / medium / high
- summary: one-line summary of what needs to be done
- has_pr: true if an open PR already addresses this issue, false otherwise

Issues:
{json.dumps(issues, indent=2, default=str)}{pr_section}

Return a JSON array of objects with keys: number, title, difficulty, urgency, summary, has_pr."""

    raw = _call(prompt, api_key, SYSTEM)
    log.info("analyze_issues raw response (first 500 chars): %s", raw[:500])
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]  # remove ```json line
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text)


def suggest_next(issues: list[dict], api_key: str | None = None) -> str:
    """Suggest which issue to work on next. Returns readable text."""
    if not issues:
        return "No open issues found."
    prompt = f"""Given these GitHub issues with analysis, suggest which one to work on next and why. Skip issues that already have PRs (has_pr: true). Be concise (2-3 sentences).

Issues:
{json.dumps(issues, indent=2, default=str)}"""

    return _call(prompt, api_key)


def review_codebase(repo_path: str, api_key: str | None = None) -> str:
    """Run Claude on a repo to identify improvements and drawbacks.

    Uses --print mode (no edits). Returns readable review text.
    """
    prompt = (
        "Review this codebase. Identify:\n"
        "1. Clear bugs or issues that should be fixed\n"
        "2. Code quality improvements (maintainability, readability)\n"
        "3. Potential performance issues\n\n"
        "Be concise and actionable. Focus on the most impactful items (top 3-5). "
        "Skip trivial style nits."
    )
    result = subprocess.run(
        ["claude", "--print", "-p", prompt],
        cwd=repo_path, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {result.stderr.strip()}")
    return result.stdout.strip() or "No output from review."


def review_pr(pr: dict, comments: list[dict], api_key: str | None = None) -> str:
    """Review a PR's context and comments, suggest improvements."""
    comments_text = ""
    for c in comments:
        if c["type"] == "review":
            comments_text += f"- [{c['path']}:{c.get('line', '?')}] @{c['user']}: {c['body']}\n"
        else:
            comments_text += f"- @{c['user']}: {c['body']}\n"

    prompt = (
        f"Review this pull request and provide feedback.\n\n"
        f"PR #{pr['number']}: {pr['title']}\n\n"
        f"{pr.get('body', '')}\n\n"
    )
    if comments_text:
        prompt += f"Existing review comments:\n{comments_text}\n\n"
    prompt += (
        "Provide a concise review:\n"
        "1. Overall assessment (looks good / needs work / has issues)\n"
        "2. Key concerns or suggestions (top 3)\n"
        "3. Any comments that still need to be addressed\n\n"
        "Be brief and actionable."
    )
    return _call(prompt, api_key)
