from __future__ import annotations

import subprocess
import sys
from pathlib import Path


root = Path(__file__).resolve().parent.parent
packs = sorted((root / "source-packs").rglob("*.json"))
if not packs:
    raise SystemExit("No source packs found")
for pack in packs:
    subprocess.run([sys.executable, str(root / "scripts" / "import_source_pack.py"), str(pack)], check=True, cwd=root)
print(f"Imported {len(packs)} governed source packs")
