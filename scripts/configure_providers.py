"""Configure provider failover without echoing secrets to the terminal."""

from __future__ import annotations

from getpass import getpass
from pathlib import Path

from configure_ai import update_env


ROOT = Path(__file__).resolve().parent.parent


def optional_secret(label: str) -> str | None:
    value = getpass(f"{label} (Enter để bỏ qua, không hiển thị khi nhập): ").strip()
    if value and len(value) < 20:
        raise SystemExit(f"{label} có vẻ chưa đầy đủ; chưa thay đổi cấu hình.")
    return value or None


def main() -> None:
    print("Cấu hình API dự phòng cho Minh Long Legal Agent")
    values: dict[str, str] = {
        "LEGAL_AGENT_PROVIDER_ORDER": "groq,gemini,cloudflare,openai",
        "LEGAL_AGENT_ALLOW_DEMO_SOURCES": "false",
        "LEGAL_AGENT_AI_MAX_OUTPUT_TOKENS": "1400",
        "LEGAL_AGENT_AI_TIMEOUT": "60",
    }
    for env_key, label in (
        ("GROQ_API_KEY", "Groq API key"),
        ("GEMINI_API_KEY", "Gemini API key"),
        ("CLOUDFLARE_API_TOKEN", "Cloudflare API token"),
        ("OPENAI_API_KEY", "OpenAI API key"),
    ):
        secret = optional_secret(label)
        if secret:
            values[env_key] = secret

    account_id = input("Cloudflare Account ID (Enter để bỏ qua): ").strip()
    if account_id:
        values["CLOUDFLARE_ACCOUNT_ID"] = account_id

    if not any(key.endswith(("API_KEY", "API_TOKEN")) for key in values):
        raise SystemExit("Chưa nhập API nào; cấu hình hiện tại được giữ nguyên.")

    env_path = ROOT / ".env"
    update_env(env_path, values)
    print(f"Đã lưu cấu hình tại {env_path}")
    print("Hãy khởi động lại server để áp dụng thứ tự API dự phòng.")


if __name__ == "__main__":
    main()
