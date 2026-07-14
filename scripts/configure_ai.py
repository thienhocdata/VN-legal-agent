"""Safely create the local .env without echoing the API key to the terminal."""

from __future__ import annotations

from getpass import getpass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    print("Cấu hình bộ não hội thoại cho Minh Long Legal Agent")
    api_key = getpass("OpenAI API key (không hiển thị khi nhập): ").strip()
    if not api_key:
        raise SystemExit("Không có API key; chưa thay đổi cấu hình.")
    model = input("Model [gpt-5.4]: ").strip() or "gpt-5.4"
    env_path = ROOT / ".env"
    env_path.write_text(
        "\n".join([
            f"OPENAI_API_KEY={api_key}",
            f"LEGAL_AGENT_MODEL={model}",
            "LEGAL_AGENT_AI_REASONING_EFFORT=low",
            "LEGAL_AGENT_AI_MAX_OUTPUT_TOKENS=1400",
            "LEGAL_AGENT_AI_TIMEOUT=60",
            "LEGAL_AGENT_ENV=development",
            "LEGAL_AGENT_AUTH_REQUIRED=false",
            "LEGAL_AGENT_ALLOW_DEMO_SOURCES=true",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Đã lưu cấu hình tại {env_path}")
    print("Hãy khởi động lại server để bật AI conversation.")


if __name__ == "__main__":
    main()
