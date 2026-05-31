#!/usr/bin/env python3
"""Merge raw + classified lessons into knowledge_base.jsonl and agent corpus slices."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (  # noqa: E402
    CLASSIFIED_LESSONS_PATH,
    FAILURE_KB_ROOT,
    KNOWLEDGE_BASE_PATH,
    RAW_LESSONS_PATH,
)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_knowledge_base(raw: list[dict], classified: list[dict]) -> list[dict]:
    raw_by_id = {r["lesson_number"]: r for r in raw}
    kb = []
    for c in classified:
        ln = c["lesson_number"]
        merged = {**raw_by_id.get(ln, {}), **c}
        kb.append(merged)
    return kb


def write_agent_slices(kb: list[dict], agents_dir: Path) -> None:
    agents: set[str] = set()
    for row in kb:
        agents.add(row["primary_agent"])
        agents.update(row.get("secondary_agents", []))

    for agent_id in sorted(agents):
        slice_rows = [
            r for r in kb
            if r.get("primary_agent") == agent_id
            or agent_id in r.get("secondary_agents", [])
        ]
        out = agents_dir / agent_id / "corpus.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for row in slice_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"  {agent_id}: {len(slice_rows)} lessons", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=RAW_LESSONS_PATH)
    parser.add_argument("--classified", type=Path, default=CLASSIFIED_LESSONS_PATH)
    parser.add_argument("--output", type=Path, default=KNOWLEDGE_BASE_PATH)
    parser.add_argument("--agents-dir", type=Path, default=FAILURE_KB_ROOT / "agents")
    args = parser.parse_args()

    raw = load_jsonl(args.raw)
    classified = load_jsonl(args.classified)
    kb = build_knowledge_base(raw, classified)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for row in kb:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(kb)} records to {args.output}", file=sys.stderr)

    print("Agent corpus slices:", file=sys.stderr)
    write_agent_slices(kb, args.agents_dir)


if __name__ == "__main__":
    main()
