from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    root: Path
    database_path: str
    auth_required: bool
    environment: str
    allow_demo_sources: bool
    ai_provider: str = "openai"
    openai_api_key: str | None = field(default=None, repr=False)
    ai_model: str = "gpt-5.4"
    ai_base_url: str | None = None
    gemini_api_key: str | None = field(default=None, repr=False)
    gemini_model: str = "gemini-3-flash-preview"
    ai_timeout_seconds: float = 60.0
    ai_max_output_tokens: int = 1400
    ai_reasoning_effort: str = "low"
    provider_order: tuple[str, ...] = ("groq", "gemini", "cloudflare", "openai")
    groq_api_key: str | None = field(default=None, repr=False)
    groq_model: str = "openai/gpt-oss-120b"
    cloudflare_api_token: str | None = field(default=None, repr=False)
    cloudflare_account_id: str | None = field(default=None, repr=False)
    cloudflare_model: str = "@cf/openai/gpt-oss-120b"

    @classmethod
    def load(cls) -> "Settings":
        root = Path(__file__).resolve().parent.parent
        load_dotenv(root / ".env", override=False)
        env = os.getenv("LEGAL_AGENT_ENV", "development").lower()
        auth_value = os.getenv("LEGAL_AGENT_AUTH_REQUIRED")
        auth_required = (env != "development") if auth_value is None else auth_value.lower() in {"1", "true", "yes"}
        demo_value = os.getenv("LEGAL_AGENT_ALLOW_DEMO_SOURCES")
        # Demo legal rules must be explicitly enabled. Development mode alone
        # is not permission to hide a missing governed corpus.
        allow_demo = False if demo_value is None else demo_value.lower() in {"1", "true", "yes"}
        legacy_provider = os.getenv("LEGAL_AGENT_PROVIDER", "").strip().lower()
        configured_order = os.getenv("LEGAL_AGENT_PROVIDER_ORDER", "").strip()
        if configured_order:
            provider_order = tuple(
                item.strip().lower() for item in configured_order.split(",") if item.strip()
            )
        elif legacy_provider:
            provider_order = tuple(dict.fromkeys(
                [legacy_provider, "groq", "gemini", "cloudflare", "openai"]
            ))
        else:
            provider_order = ("groq", "gemini", "cloudflare", "openai")
        return cls(
            root=root,
            database_path=os.getenv("LEGAL_AGENT_DB", str(root / "data" / "legal_agent.db")),
            auth_required=auth_required,
            environment=env,
            allow_demo_sources=allow_demo,
            ai_provider=os.getenv("LEGAL_AGENT_PROVIDER", "openai").strip().lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            ai_model=os.getenv("LEGAL_AGENT_MODEL", "gpt-5.4"),
            ai_base_url=os.getenv("OPENAI_BASE_URL") or None,
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
            ai_timeout_seconds=float(os.getenv("LEGAL_AGENT_AI_TIMEOUT", "60")),
            ai_max_output_tokens=int(os.getenv("LEGAL_AGENT_AI_MAX_OUTPUT_TOKENS", "1400")),
            ai_reasoning_effort=os.getenv("LEGAL_AGENT_AI_REASONING_EFFORT", "low"),
            provider_order=provider_order,
            groq_api_key=os.getenv("GROQ_API_KEY") or None,
            groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            cloudflare_api_token=os.getenv("CLOUDFLARE_API_TOKEN") or None,
            cloudflare_account_id=os.getenv("CLOUDFLARE_ACCOUNT_ID") or None,
            cloudflare_model=os.getenv("CLOUDFLARE_MODEL", "@cf/openai/gpt-oss-120b"),
        )
