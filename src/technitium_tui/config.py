"""Persistent configuration for technitium-tui."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "technitium-tui"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    server_url: str = ""
    username: str = "admin"
    token: str = ""
    stats_type: str = "LastDay"  # LastHour, LastDay, LastWeek, LastMonth, LastYear

    @classmethod
    def load(cls) -> "AppConfig":
        try:
            if CONFIG_FILE.exists():
                raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                valid = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__}
                return cls(**valid)
        except Exception:
            pass
        return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        try:
            CONFIG_FILE.chmod(0o600)
        except OSError:
            pass
