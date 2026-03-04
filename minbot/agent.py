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


def review_codebase(repo_path: str, existing_issues: list[dict] | None = None, api_key: str | None = None) -> list[dict]:
    """Run Claude on a repo to identify improvements and drawbacks.

    Uses --print mode (no edits). Returns list of {title, body} dicts
    suitable for creating GitHub issues.

    Args:
        repo_path: Path to the cloned repo.
        existing_issues: Current open issues [{number, title, body}, ...] to avoid duplicates.
        api_key: Optional Anthropic API key (unused here, kept for signature consistency).
    """
    system = (
        "You are a code reviewer. You analyze codebases and identify actionable improvements. "
        "Respond in JSON only. No markdown fences."
    )
    issues_section = ""
    if existing_issues:
        items = "\n".join(f"- #{i['number']}: {i['title']}" for i in existing_issues)
        issues_section = (
            f"\n\nThe following issues already exist in the tracker. "
            f"Do NOT suggest anything that overlaps with these:\n{items}\n"
        )
    prompt = (
        "Review this codebase. Identify the top 3-5 most impactful improvements:\n"
        "- Clear bugs or issues that should be fixed\n"
        "- Code quality improvements (maintainability, readability)\n"
        "- Potential performance issues\n\n"
        "Skip trivial style nits. Each item should be actionable.\n"
        f"{issues_section}\n"
        "Return a JSON array of objects with keys:\n"
        "- title: concise issue title (imperative, e.g. 'Fix race condition in worker')\n"
        "- body: detailed description of the problem and suggested fix"
    )
    result = subprocess.run(
        ["claude", "--print", "-p", f"{system}\n\n{prompt}"],
        cwd=repo_path, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {result.stderr.strip()}")
    raw = result.stdout.strip()
    if not raw:
        return []
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text)
