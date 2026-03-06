"""Run retention cleanup against production tables."""

from __future__ import annotations

import json

from app.config import RETENTION_DAYS
from app.db.production_store import run_retention_cleanup


def main() -> None:
    result = run_retention_cleanup(retention_days=RETENTION_DAYS)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
