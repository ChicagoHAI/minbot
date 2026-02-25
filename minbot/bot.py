"""Telegram bot entry point."""

import asyncio
import logging
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
        issues = github.list_issues(repo)
        if not issues:
            continue
        analyzed = agent.analyze_issues(issues, config.anthropic_api_key)
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
        prs = github.list_prs(repo)
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
        issues = github.list_issues(repo)
        if not issues:
            continue
        analyzed = agent.analyze_issues(issues, config.anthropic_api_key)
        for a in analyzed:
            a["repo"] = repo
        all_analyzed.extend(analyzed)

    if not all_analyzed:
        await update.message.reply_text("No open issues to suggest.")
        return

    suggestion = agent.suggest_next(all_analyzed, config.anthropic_api_key)
    await update.message.reply_text(suggestion)


async def cmd_work(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _current_task
    config = _get_config()
    if not _authorized(update, config):
        return

    if not ctx.args:
        await update.message.reply_text("Usage: /work <number> or /work <repo> <number>")
        return

    # Parse args: /work <number> (single repo) or /work <repo> <number>
    if len(ctx.args) == 1:
        if len(config.github_repos) != 1:
            await update.message.reply_text(
                "Multiple repos configured. Usage: /work <repo> <number>"
            )
            return
        repo = config.github_repos[0]
        number = int(ctx.args[0])
    else:
        repo = ctx.args[0]
        number = int(ctx.args[1])

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
