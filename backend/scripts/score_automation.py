"""
Score O*NET tasks for AI-assistability. The ONLY offline Gemini use.

Reads tasks from cache/reference.json, scores each 0-1 against a fixed rubric,
outputs cache/automation_tasks.json.

Uses google-genai SDK with structured JSON output, temperature 0.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from google import genai
from google.genai import types

from backend.config import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "backend" / "cache"
REFERENCE_PATH = CACHE_DIR / "reference.json"

RUBRIC = """Score each software development task for AI-assistability on a 0.0 to 1.0 scale.

AI-assistability means: how much of this task can a current AI coding assistant
(like GitHub Copilot, Cursor, or similar tools) handle autonomously or with
minimal human guidance?

Scoring rubric:
- 0.0-0.2: Requires deep human judgment, stakeholder interaction, creative
  problem-solving, or domain expertise that AI cannot replicate.
  Examples: requirements gathering, architecture decisions, team leadership,
  client negotiations, mentoring.
- 0.2-0.4: Partially assistable. AI can draft initial content or suggest
  approaches, but a human must make most decisions.
  Examples: code review, system design, debugging complex issues, security analysis.
- 0.4-0.6: Moderately assistable. AI can handle significant portions with
  human oversight and course correction.
  Examples: writing standard CRUD code, API integration, data transformation,
  writing documentation from existing code.
- 0.6-0.8: Highly assistable. AI can do most of the work; human reviews output.
  Examples: writing unit tests from specifications, boilerplate code generation,
  code formatting/refactoring, generating documentation.
- 0.8-1.0: Almost fully automatable. AI handles it end-to-end.
  Examples: auto-generating type stubs, formatting, simple regex patterns,
  repetitive template code.

For each task, return:
- potential: float 0.0-1.0 (the AI-assistability score)
- rationale: one SHORT sentence explaining the score (under 15 words)
"""


TASK_SCHEMA = types.Schema(
    type="OBJECT",
    properties={
        "scored_tasks": types.Schema(
            type="ARRAY",
            items=types.Schema(
                type="OBJECT",
                properties={
                    "task_id": types.Schema(type="STRING"),
                    "potential": types.Schema(type="NUMBER"),
                    "rationale": types.Schema(type="STRING"),
                },
                required=["task_id", "potential", "rationale"],
            ),
        ),
    },
    required=["scored_tasks"],
)


def score_batch(
    client: genai.Client, tasks: list[dict], model: str,
) -> dict[str, dict]:
    task_list_text = "\n".join(
        f"- task_id={t['task_id']}: {t['task']}" for t in tasks
    )
    prompt = f"""{RUBRIC}

Tasks to score:

{task_list_text}

Score every task listed above."""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_schema=TASK_SCHEMA,
        ),
    )

    if not response.text:
        print(f"WARNING: Empty response for batch of {len(tasks)} tasks")
        return {}

    try:
        scored_raw = json.loads(response.text)
    except json.JSONDecodeError:
        print(f"WARNING: Invalid JSON in response, falling back to defaults")
        return {}

    result = {}
    for s in scored_raw.get("scored_tasks", []):
        result[s["task_id"]] = s

    if response.usage_metadata:
        print(f"  Tokens: in={response.usage_metadata.prompt_token_count}, "
              f"out={response.usage_metadata.candidates_token_count}")

    return result


def main() -> None:
    if not settings.gemini_api_key:
        print("ERROR: GEMINI_API_KEY not set. Add it to .env")
        sys.exit(1)

    if not REFERENCE_PATH.exists():
        print(f"ERROR: {REFERENCE_PATH} not found. Run fetch_reference.py first.")
        sys.exit(1)

    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    onet_tasks = reference.get("onet_tasks", {})

    code_tasks: dict[str, list[dict]] = {}
    for code, tasks in onet_tasks.items():
        for t in tasks:
            code_tasks.setdefault(code, []).append({
                "task_id": t["task_id"],
                "onet_code": code,
                "task": t["task"],
                "task_type": t.get("task_type", "Core"),
            })

    total = sum(len(v) for v in code_tasks.values())
    if total == 0:
        print("ERROR: No tasks found in reference.json")
        sys.exit(1)

    print(f"Scoring {total} tasks across {len(code_tasks)} O*NET codes...")

    client = genai.Client(api_key=settings.gemini_api_key)
    scored_map: dict[str, dict] = {}

    for code, tasks in code_tasks.items():
        print(f"\n  Scoring {code} ({len(tasks)} tasks)...")
        batch_results = score_batch(client, tasks, settings.gemini_model)
        scored_map.update(batch_results)
        print(f"  Got scores for {len(batch_results)}/{len(tasks)} tasks")

    output: list[dict] = []
    for code, tasks in code_tasks.items():
        n = len(tasks)
        time_share_each = 1.0 / n if n > 0 else 0.0

        for t in tasks:
            scored = scored_map.get(t["task_id"], {})
            output.append({
                "task_id": t["task_id"],
                "onet_code": t["onet_code"],
                "task": t["task"],
                "time_share": round(time_share_each, 6),
                "potential": round(scored.get("potential", 0.3), 2),
                "rationale": scored.get("rationale", "No rationale provided"),
                "reviewed": False,
            })

    out_path = CACHE_DIR / "automation_tasks.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path} ({len(output)} tasks)")

    print("\n=== Review Table ===")
    print(f"{'Code':<14} {'Task ID':<8} {'Share':>6} {'Pot':>5}  Task (truncated)")
    print("-" * 90)

    for code in sorted(code_tasks.keys()):
        code_items = [o for o in output if o["onet_code"] == code]
        total_pot = sum(o["time_share"] * o["potential"] for o in code_items)
        for o in code_items:
            task_short = o["task"][:50] + "..." if len(o["task"]) > 50 else o["task"]
            print(f"{o['onet_code']:<14} {o['task_id']:<8} {o['time_share']:>6.3f} {o['potential']:>5.2f}  {task_short}")
        print(f"  -> {code} weighted avg potential: {total_pot:.2f}")
        low = total_pot * 0.5 * 0.7
        high = total_pot * 0.5 * 1.3
        print(f"  -> Hours saved (adoption=0.5, +/-30%): {low:.0%} - {high:.0%}")
        print()

    total_all = sum(o["time_share"] * o["potential"] for o in output) / len(code_tasks)
    print(f"Overall avg weighted potential: {total_all:.2f}")
    print(f"With adoption=0.5: ~{total_all * 0.5:.0%} of routine hours")
    print(f"Range (+/-30%): {total_all * 0.5 * 0.7:.0%} - {total_all * 0.5 * 1.3:.0%}")


if __name__ == "__main__":
    main()
