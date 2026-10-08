"""
Fetch ESCO data (live API) and read O*NET data (local xlsx files).
Output: backend/cache/reference.json

Run once during prep, never at demo time.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ESCO_BASE = "https://ec.europa.eu/esco/api"

SW_DEV_URI = (
    "http://data.europa.eu/esco/occupation/"
    "f2b15a0e-e65a-438a-affb-29b9d50b77d1"
)
UI_DEV_URI: str | None = None

ONET_CODES = ("15-1254.00", "15-1252.00")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ONET_RAW_DIR = PROJECT_ROOT / "backend" / "data" / "onet_raw"
CACHE_DIR = PROJECT_ROOT / "backend" / "cache"


def esco_related(uri: str, relation: str) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while True:
        for attempt in range(3):
            try:
                r = requests.get(
                    f"{ESCO_BASE}/resource/related",
                    timeout=20,
                    params={
                        "uri": uri,
                        "relation": relation,
                        "language": "en",
                        "limit": 50,
                        "offset": offset,
                    },
                )
                r.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(1 * (attempt + 1))
        body = r.json()
        items = body.get("_embedded", {}).get(relation, [])
        out.extend({"title": s["title"], "uri": s["uri"]} for s in items)
        if len(items) < 50:
            return out
        offset += 1


def esco_search(text: str) -> list[dict]:
    r = requests.get(
        f"{ESCO_BASE}/search",
        timeout=20,
        params={"text": text, "type": "occupation", "language": "en", "limit": 10},
    )
    r.raise_for_status()
    results = r.json().get("_embedded", {}).get("results", [])
    return [{"title": r["title"], "uri": r["uri"]} for r in results]


def esco_alternative_labels(uri: str) -> list[str]:
    r = requests.get(
        f"{ESCO_BASE}/resource/occupation",
        timeout=20,
        params={"uri": uri, "language": "en"},
    )
    if r.status_code == 200:
        body = r.json()
        labels = body.get("alternativeLabel", {}).get("en", [])
        if labels:
            return labels

    r2 = requests.get(
        f"{ESCO_BASE}/search",
        timeout=20,
        params={"text": "software developer", "type": "occupation", "language": "en", "limit": 1},
    )
    r2.raise_for_status()
    results = r2.json().get("_embedded", {}).get("results", [])
    if results:
        return results[0].get("alternativeLabel", {}).get("en", [])
    return []


def find_onet_dir() -> tuple[Path, str]:
    if not ONET_RAW_DIR.exists():
        print(f"ERROR: O*NET raw directory not found at {ONET_RAW_DIR}")
        print("Please unzip the O*NET Database download into backend/data/onet_raw/")
        sys.exit(1)

    for candidate in sorted(ONET_RAW_DIR.rglob("Task Statements.*")):
        version_dir = candidate.parent
        version = version_dir.name
        return version_dir, version

    print("ERROR: Could not find 'Task Statements.xlsx' (or .txt) in", ONET_RAW_DIR)
    print("Please download and unzip the O*NET Database into backend/data/onet_raw/")
    sys.exit(1)


def read_onet_file(onet_dir: Path, name: str) -> pd.DataFrame:
    xlsx = onet_dir / f"{name}.xlsx"
    tsv = onet_dir / f"{name}.txt"
    if xlsx.exists():
        return pd.read_excel(xlsx)
    elif tsv.exists():
        return pd.read_csv(tsv, sep="\t", encoding="utf-8")
    else:
        print(f"ERROR: Missing O*NET file: neither {xlsx} nor {tsv} exists.")
        print(f"Please add '{name}.xlsx' or '{name}.txt' to {onet_dir}")
        sys.exit(1)


def load_onet_tasks(onet_dir: Path) -> dict[str, list[dict]]:
    df = read_onet_file(onet_dir, "Task Statements")
    result = {}
    for code in ONET_CODES:
        subset = df[df["O*NET-SOC Code"] == code]
        rows = []
        for _, r in subset.iterrows():
            rows.append({
                "task_id": str(r["Task ID"]),
                "task": r["Task"],
                "task_type": r.get("Task Type", "Core"),
            })
        result[code] = rows
    return result


def load_onet_tech(onet_dir: Path) -> dict[str, list[dict]]:
    df = read_onet_file(onet_dir, "Software Skills")
    result = {}
    for code in ONET_CODES:
        subset = df[df["O*NET-SOC Code"] == code]
        seen = set()
        rows = []
        for _, r in subset.iterrows():
            example = r["Workplace Example"]
            if example in seen:
                continue
            seen.add(example)
            rows.append({
                "example": example,
                "commodity_title": r.get("Element Name", ""),
                "hot_technology": r.get("Hot Technology", "N") == "Y",
                "in_demand": r.get("In Demand", "N") == "Y",
            })
        result[code] = rows
    return result


def load_onet_titles(onet_dir: Path) -> dict[str, list[dict]]:
    result: dict[str, list[str]] = {}

    job_titles_df = read_onet_file(onet_dir, "Job Titles")
    for code in ONET_CODES:
        subset = job_titles_df[job_titles_df["O*NET-SOC Code"] == code]
        titles = subset["Job Title"].dropna().unique().tolist()
        result.setdefault(code, []).extend(titles)

    reported_df = read_onet_file(onet_dir, "Sample of Reported Titles")
    for code in ONET_CODES:
        subset = reported_df[reported_df["O*NET-SOC Code"] == code]
        titles = subset["Reported Job Title"].dropna().unique().tolist()
        existing = set(result.get(code, []))
        result.setdefault(code, []).extend(t for t in titles if t not in existing)

    return {code: [{"title": t} for t in titles] for code, titles in result.items()}


def find_ui_dev_uri() -> str:
    results = esco_search("user interface developer")
    for r in results:
        if "user interface" in r["title"].lower() and "developer" in r["title"].lower():
            return r["uri"]
    if results:
        for r in results:
            if "2512.4" in r.get("uri", "") or "interface" in r["title"].lower():
                return r["uri"]
    print("WARNING: Could not find 'user interface developer' in ESCO search.")
    print("Search results:", results)
    return ""


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("=== ESCO: fetching essential skills for software developer ===")
    try:
        esco_essential = esco_related(SW_DEV_URI, "hasEssentialSkill")
        print(f"  Got {len(esco_essential)} essential skills")
    except Exception as e:
        print(f"ERROR: ESCO API unreachable: {e}")
        sys.exit(1)

    print("=== ESCO: fetching optional skills for software developer ===")
    try:
        esco_optional = esco_related(SW_DEV_URI, "hasOptionalSkill")
        print(f"  Got {len(esco_optional)} optional skills")
    except Exception as e:
        print(f"WARNING: Could not fetch optional skills: {e}")
        esco_optional = []

    print("=== ESCO: searching for user interface developer URI ===")
    ui_dev_uri = find_ui_dev_uri()
    print(f"  UI developer URI: {ui_dev_uri}")

    print("=== ESCO: fetching alternative labels for software developer ===")
    esco_alt_labels = esco_alternative_labels(SW_DEV_URI)
    print(f"  Got {len(esco_alt_labels)} alternative labels")
    if esco_alt_labels:
        for lbl in esco_alt_labels[:10]:
            print(f"    - {lbl}")

    print("=== O*NET: reading local files ===")
    onet_dir, onet_version = find_onet_dir()
    print(f"  O*NET directory: {onet_dir}")
    print(f"  O*NET version: {onet_version}")

    onet_tasks = load_onet_tasks(onet_dir)
    for code, tasks in onet_tasks.items():
        print(f"  Tasks for {code}: {len(tasks)}")

    onet_tech = load_onet_tech(onet_dir)
    for code, techs in onet_tech.items():
        print(f"  Tech skills for {code}: {len(techs)}")

    onet_titles = load_onet_titles(onet_dir)
    for code, titles in onet_titles.items():
        print(f"  Title variants for {code}: {len(titles)}")

    reference = {
        "fetched_on": datetime.now(timezone.utc).isoformat(),
        "onet_version": onet_version,
        "esco_software_developer_uri": SW_DEV_URI,
        "esco_ui_developer_uri": ui_dev_uri,
        "esco_essential": esco_essential,
        "esco_optional": esco_optional,
        "esco_alt_labels": esco_alt_labels,
        "onet_tasks": onet_tasks,
        "onet_tech": onet_tech,
        "onet_titles": onet_titles,
    }

    out_path = CACHE_DIR / "reference.json"
    out_path.write_text(json.dumps(reference, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path} ({out_path.stat().st_size:,} bytes)")

    role_path = PROJECT_ROOT / "backend" / "data" / "taxonomy" / "canonical_role.json"
    if ui_dev_uri and role_path.exists():
        roles = json.loads(role_path.read_text(encoding="utf-8"))
        roles[0]["esco_complement_uri"] = ui_dev_uri
        role_path.write_text(json.dumps(roles, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Updated canonical_role.json with esco_complement_uri = {ui_dev_uri}")


if __name__ == "__main__":
    main()
