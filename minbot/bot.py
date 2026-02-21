"""Telegram bot entry point."""

import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
)
from minbot import github, agent, worker, scheduler
from minbot.config import load_config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_current_task: asyncio.Task | None = None


def _get_config():
    return load_config()


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "minbot is running. Commands:\n"
        "/issues - list issues with estimates\n"
        "/work <number> - work on an issue\n"
        "/status - check current work status\n"
        "/suggest - get suggestion on what to work on"
    )


async def cmd_issues(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config = _get_config()
    await update.message.reply_text("Fetching issues...")
    issues = github.list_issues(config.github_repo)
    if not issues:
        await update.message.reply_text("No open issues.")
        return

    analyzed = agent.analyze_issues(config.anthropic_api_key, issues)
    text = ""
    for a in analyzed:
        text += (
            f"#{a['number']} {a['title']}\n"
            f"  Difficulty: {a['difficulty']} | Urgency: {a['urgency']}\n"
            f"  {a['summary']}\n\n"
        )
    await update.message.reply_text(text or "No issues found.")


async def cmd_suggest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    config = _get_config()
    issues = github.list_issues(config.github_repo)
    analyzed = agent.analyze_issues(config.anthropic_api_key, issues)
    suggestion = agent.suggest_next(config.anthropic_api_key, analyzed)
    await update.message.reply_text(suggestion)


async def cmd_work(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global _current_task
    if not ctx.args:
        await update.message.reply_text("Usage: /work <issue_number>")
        return

    config = _get_config()
    number = int(ctx.args[0])
    issue = github.get_issue(config.github_repo, number)

    if _current_task and not _current_task.done():
        await update.message.reply_text("Already working on something. Check /status.")
        return

    await update.message.reply_text(f"Starting work on #{number}: {issue['title']}")

    async def on_output(text: str):
        # Send periodic updates (throttled)
        pass

    async def do_work():
        try:
            result = await worker.work_on_issue(
                config.repo_path, config.github_repo, issue, on_output,
            )
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    _current_task = asyncio.create_task(do_work())


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if _current_task is None:
        await update.message.reply_text("No work in progress.")
    elif _current_task.done():
        await update.message.reply_text("Last task completed.")
    else:
        await update.message.reply_text("Work in progress...")


def main():
    config = load_config()
    app = Application.builder().token(config.telegram_token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("issues", cmd_issues))
    app.add_handler(CommandHandler("suggest", cmd_suggest))
    app.add_handler(CommandHandler("work", cmd_work))
    app.add_handler(CommandHandler("status", cmd_status))

    async def send_message(text: str):
        await app.bot.send_message(chat_id=config.telegram_chat_id, text=text)

    async def post_init(application):
        scheduler.start(config, send_message)

    app.post_init = post_init

    log.info("Starting minbot...")
    app.run_polling()


if __name__ == "__main__":
    main()
