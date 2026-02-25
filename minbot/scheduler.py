"""Periodic issue checking and proactive suggestions."""

import json
import logging
import traceback
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from minbot import github, agent


log = logging.getLogger(__name__)
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
    try:
        known = _load_known_issues()
        found_new = False

        for repo in config.github_repos:
            issues = github.list_issues(repo)
            current = {i["number"] for i in issues}
            prev = known.get(repo, set())
            new_numbers = current - prev

            if repo in known and new_numbers:
                found_new = True
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

        if not found_new:
            await send_message("Issue check: no new issues.")
    except Exception as e:
        log.error("Issue check failed: %s", traceback.format_exc())
        await send_message(f"Issue check failed: {e}")


async def _send_suggestions(config, send_message):
    """Proactively suggest what to work on next across all repos."""
    try:
        all_analyzed = []
        for repo in config.github_repos:
            try:
                issues = github.list_issues(repo)
                analyzed = agent.analyze_issues(issues, config.anthropic_api_key)
                for a in analyzed:
                    a["repo"] = repo
                all_analyzed.extend(analyzed)
            except Exception as e:
                log.error("Failed to analyze %s: %s", repo, e)
                await send_message(f"Failed to analyze {repo}: {e}")

        if not all_analyzed:
            await send_message("No open issues to suggest.")
            return

        suggestion = agent.suggest_next(all_analyzed, config.anthropic_api_key)
        await send_message(f"Work suggestion:\n\n{suggestion}")
    except Exception as e:
        log.error("Suggestion failed: %s", traceback.format_exc())
        await send_message(f"Suggestion failed: {e}")


def start(config, send_message) -> AsyncIOScheduler:
    """Start the periodic issue checker and suggestion jobs."""
    global _scheduler
    _scheduler = AsyncIOScheduler(job_defaults={"misfire_grace_time": 3600})
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
    # Run both immediately on startup
    _scheduler.add_job(_check_issues, args=[config, send_message])
    _scheduler.add_job(_send_suggestions, args=[config, send_message])
    _scheduler.start()
    return _scheduler


def stop():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
