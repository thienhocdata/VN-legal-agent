"""Build a portable source ZIP from Git while refusing common secret leaks."""

from __future__ import annotations

import argparse
import re
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN_PATH_PARTS = {".git", ".env", "__pycache__", ".pytest_cache"}
SECRET_PATTERNS = (
    re.compile(rb"sk-proj-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"AIza[A-Za-z0-9_-]{20,}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def validate_archive(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            parts = set(Path(info.filename).parts)
            if parts & FORBIDDEN_PATH_PARTS:
                raise RuntimeError(f"Archive contains forbidden path: {info.filename}")
            if info.file_size > 5_000_000:
                continue
            payload = archive.read(info)
            if any(pattern.search(payload) for pattern in SECRET_PATTERNS):
                raise RuntimeError(f"Possible secret detected in: {info.filename}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build portable release ZIP from committed files")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "dist" / "minhlong-legal-agent.zip"
    )
    args = parser.parse_args()
    tracked_env = subprocess.run(
        ["git", "ls-files", ".env"], cwd=ROOT, text=True,
        capture_output=True, check=True,
    ).stdout.strip()
    if tracked_env:
        raise SystemExit("Refusing release: .env is tracked by Git.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "archive", "--format=zip", f"--output={args.output}", "HEAD"],
        cwd=ROOT, check=True,
    )
    try:
        validate_archive(args.output)
    except Exception:
        args.output.unlink(missing_ok=True)
        raise
    print(f"Release archive ready: {args.output}")


if __name__ == "__main__":
    main()
