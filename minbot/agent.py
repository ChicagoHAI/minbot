"""LLM reasoning for issue triage and suggestions."""

import json
import anthropic

SYSTEM = """You are a software development triage assistant. You analyze GitHub issues and estimate their difficulty and urgency.

Respond in JSON only. No markdown fences."""


def _call(api_key: str, prompt: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def analyze_issues(api_key: str, issues: list[dict]) -> list[dict]:
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

    return json.loads(_call(api_key, prompt))


def suggest_next(api_key: str, issues: list[dict]) -> str:
    """Suggest which issue to work on next. Returns readable text."""
    if not issues:
        return "No open issues found."
    prompt = f"""Given these GitHub issues with analysis, suggest which one to work on next and why. Be concise (2-3 sentences).

Issues:
{json.dumps(issues, indent=2, default=str)}"""

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text
