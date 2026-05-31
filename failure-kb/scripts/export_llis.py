#!/usr/bin/env python3
"""Export all NASA LLIS lessons via the public Elasticsearch API."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (  # noqa: E402
    LLIS_SEARCH_URL,
    RAW_LESSONS_PATH,
    normalize_organization,
    normalize_topics,
    strip_html,
)

BATCH_SIZE = 200
RATE_LIMIT_SECONDS = 0.3


def normalize_record(source: dict, hit_id: str | None = None) -> dict:
    lesson_number = str(source.get("lesson_number") or hit_id or source.get("_id") or "")
    lesson_date = source.get("lesson_date") or ""
    if not lesson_date and source.get("lessonDate"):
        # Fallback: parse "Thu Sep 21 00:00:00 GMT 2023" style dates loosely
        raw_date = source["lessonDate"]
        parts = raw_date.split()
        if len(parts) >= 6:
            lesson_date = parts[-1] + "-" + _month_to_num(parts[1]) + "-" + parts[2].zfill(2)

    program_phase = source.get("programPhase") or source.get("program_phase") or ""
    if program_phase == "None":
        program_phase = ""

    return {
        "lesson_number": lesson_number,
        "url": f"https://llis.nasa.gov/lesson/{lesson_number}",
        "title": strip_html(source.get("title")),
        "lesson_date": lesson_date,
        "organization": normalize_organization(source.get("organization")),
        "program_phase": program_phase,
        "program_relation": strip_html(source.get("programRelation") or ""),
        "nasa_topics": normalize_topics(source.get("categories")),
        "abstract_text": strip_html(source.get("lessonAbstract")),
        "driving_event_text": strip_html(source.get("drivingEvent")),
        "lesson_text": strip_html(source.get("lesson") or source.get("description_event")),
        "recommendation_text": strip_html(source.get("recommendation")),
    }


def _month_to_num(month: str) -> str:
    months = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
    }
    return months.get(month[:3], "01")


def fetch_all_lessons() -> list[dict]:
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    records: list[dict] = []
    offset = 0
    total = None

    while True:
        resp = session.post(
            LLIS_SEARCH_URL,
            json={
                "size": BATCH_SIZE,
                "from": offset,
                "query": {"match_all": {}},
                "sort": [{"lesson_number": "asc"}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        payload = resp.json()
        if total is None:
            total = payload["hits"]["total"]
        hits = payload["hits"]["hits"]
        if not hits:
            break
        batch = [normalize_record(h["_source"], hit_id=h.get("_id")) for h in hits]
        batch = [r for r in batch if r["lesson_number"] and r["title"]]
        records.extend(batch)
        offset += len(hits)
        print(f"  fetched {len(records)} / {total}", file=sys.stderr)
        if len(hits) < BATCH_SIZE or len(records) >= total:
            break
        time.sleep(RATE_LIMIT_SECONDS)

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Export NASA LLIS lessons to JSONL")
    parser.add_argument(
        "--output",
        type=Path,
        default=RAW_LESSONS_PATH,
        help="Output JSONL path",
    )
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print("Exporting LLIS lessons...", file=sys.stderr)
    records = fetch_all_lessons()

    with args.output.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} lessons to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
