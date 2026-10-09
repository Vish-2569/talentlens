#!/usr/bin/env python
"""Manual smoke test — calls the real Gemini API once with an ambiguous
requisition and prints the result + tokens used.

Usage:
    python -m scripts.llm_smoke

Requires GEMINI_API_KEY in .env (or environment).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings  # noqa: E402
from backend.llm import parse, get_meter, is_configured, reset  # noqa: E402

AMBIGUOUS_REQ = (
    "Looking for a developer with strong backend skills, "
    "preferably in a southern city. Should know cloud and containers. "
    "Budget around 25-30 lakhs, need someone soon."
)


def main() -> None:
    reset()
    print("=" * 60)
    print("TalentLens LLM Smoke Test")
    print("=" * 60)
    print(f"Model:       {settings.gemini_model}")
    print(f"Configured:  {is_configured()}")
    print()

    if not is_configured():
        print("ERROR: LLM not configured. Set GEMINI_API_KEY in .env")
        sys.exit(1)

    print(f"Input ({len(AMBIGUOUS_REQ)} chars):")
    print(f"  {AMBIGUOUS_REQ}")
    print()

    result = parse(AMBIGUOUS_REQ)

    if result is None:
        print("Result: None (LLM parse failed or returned invalid response)")
    else:
        print("Result:")
        print(json.dumps(result, indent=2))

    print()
    meter = get_meter().snapshot()
    print("Token meter:")
    for k, v in meter.items():
        print(f"  {k}: {v}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
