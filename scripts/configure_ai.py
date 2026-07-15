"""Safely create the local .env without echoing the API key to the terminal."""

from __future__ import annotations

from getpass import getpass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def update_env(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    updated: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key in remaining:
            updated.append(f"{key}={remaining.pop(key)}")
        else:
            updated.append(line)
    if updated and updated[-1]:
        updated.append("")
    updated.extend(f"{key}={value}" for key, value in remaining.items())
    path.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    print("Cấu hình bộ não hội thoại cho Minh Long Legal Agent")
    api_key = getpass("OpenAI API key (không hiển thị khi nhập): ").strip()
    if len(api_key) < 20:
        raise SystemExit("API key không hợp lệ hoặc chưa được dán đầy đủ; chưa thay đổi cấu hình.")
    model = input("Model [gpt-5.4]: ").strip() or "gpt-5.4"
    env_path = ROOT / ".env"
    update_env(env_path, {
        "LEGAL_AGENT_PROVIDER": "openai",
        "LEGAL_AGENT_PROVIDER_ORDER": "openai,groq,gemini,cloudflare",
        "OPENAI_API_KEY": api_key,
        "LEGAL_AGENT_MODEL": model,
        "LEGAL_AGENT_AI_REASONING_EFFORT": "low",
        "LEGAL_AGENT_AI_MAX_OUTPUT_TOKENS": "1400",
        "LEGAL_AGENT_AI_TIMEOUT": "60",
        "LEGAL_AGENT_ENV": "development",
        "LEGAL_AGENT_AUTH_REQUIRED": "false",
        "LEGAL_AGENT_ALLOW_DEMO_SOURCES": "false",
    })
    print(f"Đã lưu cấu hình tại {env_path}")
    print("Hãy khởi động lại server để bật AI conversation.")


if __name__ == "__main__":
    main()
