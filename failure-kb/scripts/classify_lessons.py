#!/usr/bin/env python3
"""Classify LLIS lessons using keyword rules + Anthropic LLM."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import jsonschema
import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (  # noqa: E402
    CLASSIFIED_LESSONS_PATH,
    FAILURE_KB_ROOT,
    RAW_LESSONS_PATH,
    TAXONOMY_PATH,
    truncate_text,
)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def load_taxonomy(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_schema(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def lesson_blob(lesson: dict) -> str:
    return " ".join([
        lesson.get("title", ""),
        lesson.get("abstract_text", ""),
        lesson.get("driving_event_text", ""),
        lesson.get("lesson_text", ""),
        lesson.get("recommendation_text", ""),
    ]).lower()


def apply_rule_hints(lesson: dict, taxonomy: dict) -> list[str]:
    blob = lesson_blob(lesson)
    hints: list[str] = []
    for agent_id, meta in taxonomy.get("agents", {}).items():
        for kw in meta.get("keywords", []):
            if re.search(rf"\b{re.escape(kw)}\b", blob, re.I):
                hints.append(agent_id)
                break
    return list(dict.fromkeys(hints))


def data_quality(lesson: dict) -> str:
    if lesson.get("driving_event_text") and lesson.get("lesson_text"):
        return "full"
    return "partial"


def build_prompt(lesson: dict, taxonomy: dict, rule_hints: list[str]) -> str:
    agents_text = "\n".join(
        f"- {aid}: {meta['description'].strip()}"
        for aid, meta in taxonomy["agents"].items()
    )
    patterns_text = "\n".join(
        f"- {pid}: {meta['description'].strip()}"
        for pid, meta in taxonomy["failure_patterns"].items()
    )
    hints = ", ".join(rule_hints) if rule_hints else "none"

    lesson_body = truncate_text(
        f"Title: {lesson.get('title', '')}\n"
        f"Abstract: {lesson.get('abstract_text', '')}\n"
        f"Driving event: {lesson.get('driving_event_text', '')}\n"
        f"Lesson: {lesson.get('lesson_text', '')}\n"
        f"Recommendation: {lesson.get('recommendation_text', '')}\n"
        f"NASA topics: {', '.join(lesson.get('nasa_topics', []))}\n"
        f"Organization: {lesson.get('organization', '')}\n"
        f"Program phase: {lesson.get('program_phase', '')}"
    )

    return f"""Classify this NASA LLIS lesson using the taxonomy below.

RULES:
- primary_agent: earliest lifecycle stage where intervention would have prevented the incident
- secondary_agents: up to 3 additional strongly supported agents (no duplicates of primary)
- failure_patterns: up to 5 multi-label pattern IDs
- evidence: 1-3 quotes max 240 chars from lesson fields, each tied to pattern/agent IDs in "supports"
- confidence: high/medium/low
- impact_severity: critical/major/minor/unknown based on stated consequences
- impact_notes: brief summary of cost/schedule/safety impact if stated, else empty string

Keyword rule hints (non-binding): {hints}

LIFECYCLE AGENTS:
{agents_text}

FAILURE PATTERNS:
{patterns_text}

LESSON:
{lesson_body}

Respond with ONLY valid JSON matching this shape:
{{
  "primary_agent": "<agent_id>",
  "secondary_agents": ["<agent_id>"],
  "failure_patterns": ["<pattern_id>"],
  "confidence": "high|medium|low",
  "evidence": [{{"quote": "...", "field": "lesson_text", "supports": ["pattern_id"]}}],
  "impact_severity": "critical|major|minor|unknown",
  "impact_notes": "..."
}}"""


FIELD_ALIASES = {
    "abstract": "abstract_text",
    "title": "title",
    "driving event": "driving_event_text",
    "driving_event": "driving_event_text",
    "lesson": "lesson_text",
    "recommendation": "recommendation_text",
}


def normalize_classification(result: dict, lesson: dict, taxonomy: dict, schema: dict) -> dict:
    valid_agents = set(taxonomy["agents"])
    valid_patterns = set(taxonomy["failure_patterns"])

    primary = result.get("primary_agent")
    if primary not in valid_agents:
        primary = next(iter(valid_agents))
    result["primary_agent"] = primary

    secondary = [
        a for a in result.get("secondary_agents", [])
        if a in valid_agents and a != primary
    ]
    result["secondary_agents"] = secondary[:3]

    patterns = [p for p in result.get("failure_patterns", []) if p in valid_patterns]
    result["failure_patterns"] = patterns[:5] or ["requirements_gap"]

    normalized_evidence = []
    for ev in result.get("evidence", []):
        field = ev.get("field", "lesson_text")
        field_key = field.lower().replace("-", "_")
        field = FIELD_ALIASES.get(field_key, field_key)
        if field not in schema["properties"]["evidence"]["items"]["properties"]["field"]["enum"]:
            field = "lesson_text"
        quote = (ev.get("quote") or "")[:240]
        supports = [s for s in ev.get("supports", []) if s in valid_patterns or s in valid_agents]
        if quote and supports:
            normalized_evidence.append({"quote": quote, "field": field, "supports": supports})
    if not normalized_evidence:
        fallback = lesson.get("lesson_text") or lesson.get("title") or ""
        normalized_evidence = [{
            "quote": fallback[:240],
            "field": "lesson_text",
            "supports": result["failure_patterns"][:1],
        }]
    result["evidence"] = normalized_evidence[:3]

    if result.get("confidence") not in schema["properties"]["confidence"]["enum"]:
        result["confidence"] = "medium"
    if result.get("impact_severity") not in schema["properties"]["impact_severity"]["enum"]:
        result["impact_severity"] = "unknown"
    result["impact_notes"] = result.get("impact_notes") or ""
    result["lesson_number"] = lesson["lesson_number"]
    result["data_quality"] = data_quality(lesson)
    return result


def classify_lesson(
    client: Anthropic,
    model: str,
    lesson: dict,
    taxonomy: dict,
    schema: dict,
    rule_hints: list[str],
    max_retries: int = 3,
) -> dict:
    prompt = build_prompt(lesson, taxonomy, rule_hints)
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
            result = json.loads(text)
            if rule_hints:
                result["rule_hints"] = rule_hints
            result = normalize_classification(result, lesson, taxonomy, schema)
            jsonschema.validate(result, schema)
            return result
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(
        f"Failed to classify lesson {lesson['lesson_number']}: {last_error}"
    )


def select_pilot_lessons(lessons: list[dict], n: int = 50) -> list[dict]:
    """10 newest + 20 random + 20 stratified by software/hardware/safety topics."""
    sorted_lessons = sorted(
        lessons,
        key=lambda x: x.get("lesson_date") or "",
        reverse=True,
    )
    newest = sorted_lessons[:10]

    remaining = [l for l in lessons if l not in newest]
    random.seed(42)
    random_pick = random.sample(remaining, min(20, len(remaining)))

    def has_topic(keywords: list[str], lesson: dict) -> bool:
        topics = " ".join(lesson.get("nasa_topics", [])).lower()
        blob = lesson_blob(lesson)
        return any(k in topics or k in blob for k in keywords)

    software = [l for l in lessons if has_topic(["software", "code"], l)]
    hardware = [l for l in lessons if has_topic(["hardware", "structural", "mechanical"], l)]
    safety = [l for l in lessons if has_topic(["safety", "hazard", "mishap"], l)]

    stratified: list[dict] = []
    for pool in [software, hardware, safety]:
        pool = [l for l in pool if l not in newest and l not in random_pick]
        stratified.extend(random.sample(pool, min(7, len(pool))))

    seen = set()
    combined: list[dict] = []
    for lesson in newest + random_pick + stratified:
        key = lesson["lesson_number"]
        if key not in seen:
            seen.add(key)
            combined.append(lesson)
        if len(combined) >= n:
            break
    return combined[:n]


def main() -> None:
    load_dotenv(FAILURE_KB_ROOT.parent / ".env")
    load_dotenv(FAILURE_KB_ROOT / ".env")

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RAW_LESSONS_PATH)
    parser.add_argument("--output", type=Path, default=CLASSIFIED_LESSONS_PATH)
    parser.add_argument("--taxonomy", type=Path, default=TAXONOMY_PATH)
    parser.add_argument(
        "--schema",
        type=Path,
        default=FAILURE_KB_ROOT / "schema" / "lesson.schema.json",
    )
    parser.add_argument("--model", default=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL))
    parser.add_argument("--limit", type=int, default=0, help="Max lessons to classify (0=all)")
    parser.add_argument("--pilot", action="store_true", help="Use 50-lesson pilot sample")
    parser.add_argument("--first", type=int, default=0, help="Classify only first N by lesson_number")
    parser.add_argument("--resume", action="store_true", help="Skip already classified lesson_numbers")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between API calls")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    taxonomy = load_taxonomy(args.taxonomy)
    schema = load_schema(args.schema)
    lessons = load_jsonl(args.input)
    lessons = [l for l in lessons if l.get("lesson_number") and l.get("title")]

    if args.pilot:
        lessons = select_pilot_lessons(lessons, 50)
    elif args.first:
        def sort_key(lesson: dict) -> tuple:
            num = lesson.get("lesson_number", "")
            return (0, int(num)) if str(num).isdigit() else (1, str(num))

        lessons = sorted(lessons, key=sort_key)[: args.first]
    elif args.limit:
        lessons = lessons[: args.limit]

    done_ids: set[str] = set()
    if args.resume and args.output.exists():
        for row in load_jsonl(args.output):
            done_ids.add(row["lesson_number"])

    client = Anthropic(api_key=api_key)
    classified = load_jsonl(args.output) if args.resume else []

    total = len(lessons)
    for i, lesson in enumerate(lessons, 1):
        ln = lesson["lesson_number"]
        if ln in done_ids:
            continue
        hints = apply_rule_hints(lesson, taxonomy)
        print(f"[{i}/{total}] Classifying {ln}...", file=sys.stderr)
        result = classify_lesson(client, args.model, lesson, taxonomy, schema, hints)
        classified.append(result)
        append_jsonl(args.output, result)
        done_ids.add(ln)
        time.sleep(args.delay)

    print(f"Classified {len(classified)} lessons total -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
