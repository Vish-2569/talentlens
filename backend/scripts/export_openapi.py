"""Export the FastAPI OpenAPI schema to openapi.json at the repo root."""
from __future__ import annotations

import json
from pathlib import Path

from backend.api.main import app

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> None:
    schema = app.openapi()
    out = _REPO_ROOT / "openapi.json"
    out.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
