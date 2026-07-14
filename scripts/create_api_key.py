from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth import issue_api_key
from app.config import Settings
from app.database import Database
from app.models import Role


parser = argparse.ArgumentParser(description="Create a Minh Long Legal Agent API key")
parser.add_argument("--actor", required=True)
parser.add_argument("--tenant", required=True)
parser.add_argument("--role", required=True, choices=[r.value for r in Role])
args = parser.parse_args()

settings = Settings.load()
key = issue_api_key(Database(settings.database_path), args.actor, args.tenant, Role(args.role))
print("API key created. Store it securely; it will not be shown again:")
print(key)
