"""Periodic issue checking."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from minbot import github, agent


_scheduler = None
_known_issues: set[int] = set()


async def _check_issues(config, send_message):
    """Check for new issues and notify via Telegram."""
    global _known_issues

    issues = github.list_issues(config.github_repo)
    current = {i["number"] for i in issues}
    new_numbers = current - _known_issues

    if _known_issues and new_numbers:
        new_issues = [i for i in issues if i["number"] in new_numbers]
        analyzed = agent.analyze_issues(config.anthropic_api_key, new_issues)
        text = "New issues found:\n\n"
        for a in analyzed:
            text += (
                f"#{a['number']} {a['title']}\n"
                f"  Difficulty: {a['difficulty']} | Urgency: {a['urgency']}\n"
                f"  {a['summary']}\n\n"
            )
        await send_message(text)

    _known_issues = current


def start(config, send_message) -> AsyncIOScheduler:
    """Start the periodic issue checker."""
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _check_issues, "interval",
        hours=config.check_interval_hours,
        args=[config, send_message],
    )
    _scheduler.start()
    return _scheduler


def stop():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
