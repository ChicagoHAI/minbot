"""Telegram bot entry point."""

import asyncio
import logging
import os
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
)
from minbot import github, agent, worker, scheduler
from minbot.config import load_config, save_config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_current_task: asyncio.Task | None = None


def _get_config():
    return load_config()


def _authorized(update: Update, config) -> bool:
    """Check if the sender matches the configured chat ID."""
    return not config.telegram_chat_id or update.effective_chat.id == config.telegram_chat_id


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config = _get_config()
    chat_id = update.effective_chat.id

    # Allow first user to claim the bot
    if config.telegram_chat_id and config.telegram_chat_id != chat_id:
        return

    if config.telegram_chat_id != chat_id:
        config.telegram_chat_id = chat_id
        save_config(config)
        log.info("Saved chat_id %s", chat_id)

    await update.message.reply_text(
        "minbot is running. Commands:\n"
        "/issues - list issues with estimates\n"
        "/prs - list open pull requests\n"
        "/work <number> or /work <repo> <number> - work on an issue\n"
        "/pr <number> [comments] - address PR review comments\n"
        "/review [repo] - run a code review\n"
        "/status - check current work status\n"
        "/suggest - get suggestion on what to work on\n"
        "/repos - list configured repos"
    )


async def cmd_repos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config = _get_config()
    if not _authorized(update, config):
        return
    text = "Configured repos:\n" + "\n".join(f"- {r}" for r in config.github_repos)
    await update.message.reply_text(text)


def _resolve_repos(config, args) -> list[str]:
    """Return repo list filtered by optional arg, or all configured repos."""
    if args:
        query = args[0].lower()
        matches = [r for r in config.github_repos if r.lower() == query]
        if matches:
            return matches
        # Try partial match (e.g. "repo" matches "owner/repo")
        matches = [r for r in config.github_repos if r.lower().endswith(f"/{query}")]
        if matches:
            return matches
        return []
    return config.github_repos


async def cmd_issues(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config = _get_config()
    if not _authorized(update, config):
        return

    repos = _resolve_repos(config, ctx.args)
    if not repos:
        await update.message.reply_text(f"Repo not found. Configured: {', '.join(config.github_repos)}")
        return

    await update.message.reply_text("Fetching issues...")

    text = ""
    for repo in repos:
        all_items = github.list_issues(repo, include_prs=True)
        issues = [i for i in all_items if not i["is_pr"]]
        prs = [i for i in all_items if i["is_pr"]]
        if not issues:
            continue
        analyzed = agent.analyze_issues(issues, config.anthropic_api_key, prs)
        text += f"[{repo}]\n"
        for a in analyzed:
            text += (
                f"#{a['number']} {a['title']}\n"
                f"  Difficulty: {a['difficulty']} | Urgency: {a['urgency']}\n"
                f"  {a['summary']}\n\n"
            )

    await update.message.reply_text(text or "No open issues.")


async def cmd_prs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config = _get_config()
    if not _authorized(update, config):
        return

    repos = _resolve_repos(config, ctx.args)
    if not repos:
        await update.message.reply_text(f"Repo not found. Configured: {', '.join(config.github_repos)}")
        return

    text = ""
    for repo in repos:
        prs = [i for i in github.list_issues(repo, include_prs=True) if i["is_pr"]]
        if not prs:
            continue
        text += f"[{repo}]\n"
        for p in prs:
            labels = ", ".join(p["labels"]) if p["labels"] else ""
            text += f"#{p['number']} {p['title']}"
            if labels:
                text += f" [{labels}]"
            text += "\n"
        text += "\n"

    await update.message.reply_text(text or "No open pull requests.")


async def cmd_suggest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config = _get_config()
    if not _authorized(update, config):
        return

    repos = _resolve_repos(config, ctx.args)
    if not repos:
        await update.message.reply_text(f"Repo not found. Configured: {', '.join(config.github_repos)}")
        return

    all_analyzed = []
    for repo in repos:
        all_items = github.list_issues(repo, include_prs=True)
        issues = [i for i in all_items if not i["is_pr"]]
        prs = [i for i in all_items if i["is_pr"]]
        if not issues:
            continue
        analyzed = agent.analyze_issues(issues, config.anthropic_api_key, prs)
        for a in analyzed:
            a["repo"] = repo
        all_analyzed.extend(analyzed)

    if not all_analyzed:
        await update.message.reply_text("No open issues to suggest.")
        return

    suggestion = agent.suggest_next(all_analyzed, config.anthropic_api_key)
    await update.message.reply_text(suggestion)


def _parse_repo_and_number(config, args):
    """Parse repo and number from command args.

    Returns (repo, number, remaining_args) or raises ValueError.
    """
    if not args:
        raise ValueError("No arguments provided.")

    # Try first arg as number (single repo mode)
    first_is_number = True
    try:
        number = int(args[0])
    except ValueError:
        first_is_number = False

    if first_is_number:
        if len(config.github_repos) != 1:
            raise ValueError("Multiple repos configured. Specify repo name.")
        return config.github_repos[0], number, args[1:]

    # First arg is repo, second is number
    if len(args) < 2:
        raise ValueError("Usage: <number> or <repo> <number>")

    repo = args[0]
    matches = _resolve_repos(config, [repo])
    if not matches:
        raise ValueError(f"Repo not found: {repo}")
    repo = matches[0]
    number = int(args[1])
    return repo, number, args[2:]


async def cmd_work(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _current_task
    config = _get_config()
    if not _authorized(update, config):
        return

    if not ctx.args:
        await update.message.reply_text("Usage: /work <number> or /work <repo> <number>")
        return

    try:
        repo, number, _ = _parse_repo_and_number(config, ctx.args)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return

    issue = github.get_issue(repo, number)

    if _current_task and not _current_task.done():
        await update.message.reply_text("Already working on something. Check /status.")
        return

    await update.message.reply_text(f"Starting work on {repo}#{number}: {issue['title']}")

    async def on_output(text: str):
        pass

    async def do_work():
        try:
            result = await worker.work_on_issue(
                config.workspace_dir, repo, issue, on_output,
            )
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    _current_task = asyncio.create_task(do_work())


async def cmd_pr(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _current_task
    config = _get_config()
    if not _authorized(update, config):
        return

    if not ctx.args:
        await update.message.reply_text(
            "Usage: /pr <number> [comments] or /pr <repo> <number> [comments]"
        )
        return

    try:
        repo, number, remaining = _parse_repo_and_number(config, ctx.args)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return

    user_instructions = " ".join(remaining)

    if _current_task and not _current_task.done():
        await update.message.reply_text("Already working on something. Check /status.")
        return

    pr = github.get_pr(repo, number)
    comments = github.get_pr_comments(repo, number)

    await update.message.reply_text(
        f"Addressing review comments on {repo} PR #{number}: {pr['title']}\n"
        f"Found {len(comments)} comment(s)."
    )

    async def on_output(text: str):
        pass

    async def do_work():
        try:
            result = await worker.address_pr_comments(
                config.workspace_dir, repo, pr, comments,
                user_instructions, on_output,
            )
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    _current_task = asyncio.create_task(do_work())


async def cmd_review(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config = _get_config()
    if not _authorized(update, config):
        return

    repos = _resolve_repos(config, ctx.args)
    if not repos:
        await update.message.reply_text(f"Repo not found. Configured: {', '.join(config.github_repos)}")
        return

    await update.message.reply_text("Starting code review...")

    async def do_review():
        try:
            for repo in repos:
                repo_path = os.path.join(config.workspace_dir, repo)
                github.clone_repo(repo, repo_path)
                existing = github.list_issues(repo, include_prs=False)
                suggestions = agent.review_codebase(repo_path, existing, config.anthropic_api_key)
                if not suggestions:
                    await update.message.reply_text(f"Review of {repo}: no suggestions.")
                    continue
                created = []
                for s in suggestions:
                    body = (
                        f"{s['body']}\n\n"
                        f"---\n"
                        f"_Identified by [minbot](https://github.com/ChicagoHAI/minbot) code review_"
                    )
                    url = github.create_issue(repo, s["title"], body)
                    created.append(f"- {s['title']}: {url}")
                await update.message.reply_text(
                    f"Review of {repo} — created {len(created)} issue(s):\n"
                    + "\n".join(created)
                )
        except Exception as e:
            await update.message.reply_text(f"Review error: {e}")

    asyncio.create_task(do_review())


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config = _get_config()
    if not _authorized(update, config):
        return
    if _current_task is None:
        await update.message.reply_text("No work in progress.")
    elif _current_task.done():
        await update.message.reply_text("Last task completed.")
    else:
        await update.message.reply_text("Work in progress...")


def main():
    config = load_config()
    github.set_token(config.github_token)
    app = Application.builder().token(config.telegram_token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("issues", cmd_issues))
    app.add_handler(CommandHandler("prs", cmd_prs))
    app.add_handler(CommandHandler("suggest", cmd_suggest))
    app.add_handler(CommandHandler("work", cmd_work))
    app.add_handler(CommandHandler("pr", cmd_pr))
    app.add_handler(CommandHandler("review", cmd_review))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("repos", cmd_repos))

    async def send_message(text: str):
        c = _get_config()
        if c.telegram_chat_id:
            await app.bot.send_message(chat_id=c.telegram_chat_id, text=text)

    async def post_init(application):
        scheduler.start(config, send_message)
        await send_message("minbot is ready.")

    app.post_init = post_init

    log.info("Starting minbot...")
    app.run_polling()


if __name__ == "__main__":
    main()
