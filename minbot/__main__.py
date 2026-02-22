import sys
from minbot.config import CONFIG_PATH, Config, save_config


def setup():
    """Interactive first-time setup. Writes config to ~/.minbot/config.json."""
    print("minbot setup\n")

    github_token = input("GitHub token: ").strip()
    telegram_token = input("Telegram bot token: ").strip()

    repos = []
    print("\nAdd GitHub repos (owner/repo format). Empty line to finish.")
    while True:
        repo = input("  repo: ").strip()
        if not repo:
            break
        repos.append(repo)

    if not repos:
        print("At least one repo is required.")
        sys.exit(1)

    interval = input("\nCheck interval in hours [6]: ").strip()
    check_interval_hours = int(interval) if interval else 6

    workspace = input("Workspace directory [/workspace]: ").strip()
    workspace_dir = workspace if workspace else "/workspace"

    config = Config(
        telegram_token=telegram_token,
        github_token=github_token,
        github_repos=repos,
        check_interval_hours=check_interval_hours,
        workspace_dir=workspace_dir,
    )
    save_config(config)
    print(f"\nConfig saved to {CONFIG_PATH}")
    print("Start the bot and send /start in Telegram to complete setup.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup()
    elif not CONFIG_PATH.exists():
        print(f"No config found at {CONFIG_PATH}. Running setup...\n")
        setup()
    else:
        from minbot.bot import main
        main()
