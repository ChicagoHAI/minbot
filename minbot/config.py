import json
from pathlib import Path
from pydantic import BaseModel

CONFIG_PATH = Path.home() / ".minbot" / "config.json"


class Config(BaseModel):
    telegram_token: str
    telegram_chat_id: int
    github_token: str
    github_repos: list[str]
    anthropic_api_key: str | None = None
    check_interval_hours: int = 6
    workspace_dir: str = "/workspace"


def load_config(path: Path = CONFIG_PATH) -> Config:
    return Config(**json.loads(path.read_text()))


def save_config(config: Config, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2))
