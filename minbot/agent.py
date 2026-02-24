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


def analyze_issues(issues: list[dict], api_key: str | None = None) -> list[dict]:
    """Estimate difficulty and urgency for each issue.

    Returns list of {number, title, difficulty, urgency, summary}.
    """
    if not issues:
        return []
    prompt = f"""Analyze these GitHub issues. For each, estimate:
- difficulty: easy / medium / hard
- urgency: low / medium / high
- summary: one-line summary of what needs to be done

Issues:
{json.dumps(issues, indent=2, default=str)}

Return a JSON array of objects with keys: number, title, difficulty, urgency, summary."""

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
    prompt = f"""Given these GitHub issues with analysis, suggest which one to work on next and why. Be concise (2-3 sentences).

Issues:
{json.dumps(issues, indent=2, default=str)}"""

    return _call(prompt, api_key)
