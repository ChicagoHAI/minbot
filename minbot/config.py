import contextlib
import json
import os
import tempfile
from pathlib import Path
from pydantic import BaseModel

CONFIG_PATH = Path.home() / ".minbot" / "config.json"


class Config(BaseModel):
    telegram_token: str
    telegram_chat_id: int | None = None
    github_token: str
    github_repos: list[str]
    anthropic_api_key: str | None = None
    check_interval_hours: int = 6
    suggest_interval_hours: int = 24
    review_interval_hours: int | None = None
    workspace_dir: str = "/workspace"


def load_config(path: Path = CONFIG_PATH) -> Config:
    return Config(**json.loads(path.read_text()))


def save_config(config: Config, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    closed = False
    try:
        os.write(fd, config.model_dump_json(indent=2).encode())
        os.fchmod(fd, 0o600)
        os.close(fd)
        closed = True
        os.rename(tmp, path)
    except BaseException:
        if not closed:
            os.close(fd)
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise
