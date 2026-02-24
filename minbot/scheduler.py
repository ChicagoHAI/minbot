"""Periodic issue checking and proactive suggestions."""

import json
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from minbot import github, agent


_scheduler = None
_KNOWN_ISSUES_PATH = Path.home() / ".minbot" / "known_issues.json"


def _load_known_issues() -> dict[str, set[int]]:
    if _KNOWN_ISSUES_PATH.exists():
        data = json.loads(_KNOWN_ISSUES_PATH.read_text())
        return {repo: set(nums) for repo, nums in data.items()}
    return {}


def _save_known_issues(known: dict[str, set[int]]) -> None:
    data = {repo: sorted(nums) for repo, nums in known.items()}
    _KNOWN_ISSUES_PATH.write_text(json.dumps(data))


async def _check_issues(config, send_message):
    """Check for new issues across all repos and notify via Telegram."""
    known = _load_known_issues()

    for repo in config.github_repos:
        issues = github.list_issues(repo)
        current = {i["number"] for i in issues}
        prev = known.get(repo, set())
        new_numbers = current - prev

        if prev and new_numbers:
            new_issues = [i for i in issues if i["number"] in new_numbers]
            analyzed = agent.analyze_issues(new_issues, config.anthropic_api_key)
            text = f"New issues in {repo}:\n\n"
            for a in analyzed:
                text += (
                    f"#{a['number']} {a['title']}\n"
                    f"  Difficulty: {a['difficulty']} | Urgency: {a['urgency']}\n"
                    f"  {a['summary']}\n\n"
                )
            await send_message(text)

        known[repo] = current

    _save_known_issues(known)


async def _send_suggestions(config, send_message):
    """Proactively suggest what to work on next across all repos."""
    all_analyzed = []
    for repo in config.github_repos:
        issues = github.list_issues(repo)
        analyzed = agent.analyze_issues(issues, config.anthropic_api_key)
        for a in analyzed:
            a["repo"] = repo
        all_analyzed.extend(analyzed)

    if not all_analyzed:
        return

    suggestion = agent.suggest_next(all_analyzed, config.anthropic_api_key)
    await send_message(f"Work suggestion:\n\n{suggestion}")


def start(config, send_message) -> AsyncIOScheduler:
    """Start the periodic issue checker and suggestion jobs."""
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _check_issues, "interval",
        hours=config.check_interval_hours,
        args=[config, send_message],
    )
    _scheduler.add_job(
        _send_suggestions, "interval",
        hours=config.suggest_interval_hours,
        args=[config, send_message],
    )
    _scheduler.start()
    return _scheduler


def stop():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
