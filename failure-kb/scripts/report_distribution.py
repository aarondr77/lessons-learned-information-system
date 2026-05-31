#!/usr/bin/env python3
"""Print distribution report for classified lessons."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import CLASSIFIED_LESSONS_PATH, KNOWLEDGE_BASE_PATH  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=KNOWLEDGE_BASE_PATH)
    parser.add_argument("--min-count", type=int, default=20)
    args = parser.parse_args()

    if not args.input.exists():
        args.input = CLASSIFIED_LESSONS_PATH
    rows = load_jsonl(args.input)
    n = len(rows)

    primary = Counter(r["primary_agent"] for r in rows)
    patterns: Counter = Counter()
    impact = Counter(r.get("impact_severity", "unknown") for r in rows)
    confidence = Counter(r.get("confidence", "unknown") for r in rows)

    for r in rows:
        patterns.update(r.get("failure_patterns", []))

    print(f"Total classified lessons: {n}\n")
    print("Primary agent distribution:")
    for agent, count in primary.most_common():
        flag = " ⚠ LOW" if count < args.min_count else ""
        print(f"  {agent}: {count}{flag}")

    print("\nFailure pattern distribution (top 20):")
    for pattern, count in patterns.most_common(20):
        print(f"  {pattern}: {count}")

    print("\nImpact severity:")
    for sev, count in impact.most_common():
        print(f"  {sev}: {count}")

    print("\nConfidence:")
    for conf, count in confidence.most_common():
        print(f"  {conf}: {count}")

    low_agents = [a for a, c in primary.items() if c < args.min_count]
    if low_agents:
        print(f"\n⚠ Agents below {args.min_count} lessons: {', '.join(low_agents)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
