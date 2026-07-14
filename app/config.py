from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root: Path
    database_path: str
    auth_required: bool
    environment: str
    allow_demo_sources: bool

    @classmethod
    def load(cls) -> "Settings":
        root = Path(__file__).resolve().parent.parent
        env = os.getenv("LEGAL_AGENT_ENV", "development").lower()
        auth_value = os.getenv("LEGAL_AGENT_AUTH_REQUIRED")
        auth_required = (env != "development") if auth_value is None else auth_value.lower() in {"1", "true", "yes"}
        demo_value = os.getenv("LEGAL_AGENT_ALLOW_DEMO_SOURCES")
        allow_demo = (env == "development") if demo_value is None else demo_value.lower() in {"1", "true", "yes"}
        return cls(root, os.getenv("LEGAL_AGENT_DB", str(root / "data" / "legal_agent.db")), auth_required, env, allow_demo)
