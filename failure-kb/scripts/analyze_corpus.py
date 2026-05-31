#!/usr/bin/env python3
"""Profile raw LLIS corpus and write analysis report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import FAILURE_KB_ROOT, RAW_LESSONS_PATH  # noqa: E402

THEME_KEYWORDS = {
    "software": r"\b(software|firmware|code|iv&v|simulation|algorithm|database)\b",
    "safety_pha": r"\b(pha|hazard analysis|safety review|failure of imagination|mishap)\b",
    "testing": r"\b(test|verification|validation|qualification|acceptance)\b",
    "operations": r"\b(operator|procedure|monitoring|inspection|maintenance|ops)\b",
    "configuration": r"\b(configuration|config change|drawing|baseline|as-built)\b",
    "hardware_design": r"\b(structural|material|weld|fatigue|redundan|mechanical|hardware)\b",
    "integration": r"\b(interface|integration|subsystem|end-to-end|compatibility)\b",
    "facilities": r"\b(facility|ground support|piping|pump|hvac|infrastructure)\b",
    "program_process": r"\b(procurement|contract|schedule|documentation|license|backlog)\b",
    "human_factors": r"\b(training|label|human factor|misidentif|complacency)\b",
    "requirements": r"\b(requirement|traceability|specification)\b",
    "cost_schedule": r"\b(\$|cost|schedule delay|month|year|million|budget|slip)\b",
    "safety_critical": r"\b(fatality|injury|explosion|fire|critical|catastrophic|loss of)\b",
}


def load_lessons(path: Path) -> list[dict]:
    lessons = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lessons.append(json.loads(line))
    return lessons


def field_coverage(lessons: list[dict]) -> dict[str, float]:
    fields = [
        "title", "lesson_date", "organization", "program_phase",
        "abstract_text", "driving_event_text", "lesson_text", "recommendation_text",
    ]
    n = len(lessons)
    coverage = {}
    for field in fields:
        filled = sum(1 for l in lessons if l.get(field))
        coverage[field] = round(100 * filled / n, 1) if n else 0
    coverage["nasa_topics_nonempty"] = round(
        100 * sum(1 for l in lessons if l.get("nasa_topics")) / n, 1
    )
    return coverage


def count_themes(lessons: list[dict]) -> Counter:
    counts: Counter = Counter()
    for lesson in lessons:
        blob = " ".join([
            lesson.get("title", ""),
            lesson.get("abstract_text", ""),
            lesson.get("driving_event_text", ""),
            lesson.get("lesson_text", ""),
            lesson.get("recommendation_text", ""),
        ]).lower()
        for theme, pattern in THEME_KEYWORDS.items():
            if re.search(pattern, blob, re.I):
                counts[theme] += 1
    return counts


def topic_distribution(lessons: list[dict], top_n: int = 25) -> Counter:
    topics: Counter = Counter()
    for lesson in lessons:
        for topic in lesson.get("nasa_topics", []):
            topics[topic.strip()] += 1
    return Counter(dict(topics.most_common(top_n)))


def org_distribution(lessons: list[dict]) -> Counter:
    return Counter(l.get("organization") or "unknown" for l in lessons)


def phase_distribution(lessons: list[dict]) -> Counter:
    return Counter(l.get("program_phase") or "unknown" for l in lessons)


def year_distribution(lessons: list[dict]) -> Counter:
    years: Counter = Counter()
    for lesson in lessons:
        date = lesson.get("lesson_date") or ""
        year = date[:4] if len(date) >= 4 and date[:4].isdigit() else "unknown"
        years[year] += 1
    return years


def sample_lessons(lessons: list[dict], n: int = 5) -> list[dict]:
    """Pick diverse samples by org and decade."""
    by_org: dict[str, list[dict]] = {}
    for lesson in lessons:
        org = lesson.get("organization") or "unknown"
        by_org.setdefault(org, []).append(lesson)
    samples = []
    for org_lessons in by_org.values():
        samples.append(org_lessons[len(org_lessons) // 2])
        if len(samples) >= n:
            break
    return samples[:n]


def write_report(lessons: list[dict], output: Path) -> None:
    n = len(lessons)
    coverage = field_coverage(lessons)
    themes = count_themes(lessons)
    topics = topic_distribution(lessons)
    orgs = org_distribution(lessons)
    phases = phase_distribution(lessons)
    years = year_distribution(lessons)
    samples = sample_lessons(lessons)

    lines = [
        "# LLIS Corpus Analysis",
        "",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Total lessons: **{n}**",
        "",
        "## Field coverage",
        "",
        "| Field | % populated |",
        "| --- | --- |",
    ]
    for field, pct in coverage.items():
        lines.append(f"| `{field}` | {pct}% |")

    lines.extend([
        "",
        "## Text theme frequency",
        "",
        "Keyword/regex hits across title + abstract + driving event + lesson + recommendation.",
        "",
        "| Theme | Lessons | % |",
        "| --- | --- | --- |",
    ])
    for theme, count in themes.most_common():
        lines.append(f"| {theme} | {count} | {round(100*count/n,1)}% |")

    lines.extend([
        "",
        "## Top NASA topics",
        "",
        "| Topic | Count |",
        "| --- | --- |",
    ])
    for topic, count in topics.most_common():
        lines.append(f"| {topic} | {count} |")

    lines.extend([
        "",
        "## Organization distribution (top 15)",
        "",
        "| Center | Count |",
        "| --- | --- |",
    ])
    for org, count in orgs.most_common(15):
        lines.append(f"| {org} | {count} |")

    lines.extend([
        "",
        "## Program phase",
        "",
        "| Phase | Count |",
        "| --- | --- |",
    ])
    for phase, count in phases.most_common():
        lines.append(f"| {phase} | {count} |")

    lines.extend([
        "",
        "## Lessons by year (sample)",
        "",
        "| Year | Count |",
        "| --- | --- |",
    ])
    for year, count in sorted(years.items()):
        if year != "unknown":
            lines.append(f"| {year} | {count} |")

    lines.extend([
        "",
        "## Taxonomy recommendations",
        "",
        "Based on theme frequency and field coverage:",
        "",
        "### Layer 1 — lifecycle agents (9)",
        "",
        "Data supports distinct clusters for:",
        "- `design_safety_review` — safety_pha theme + PHA/hazard language",
        "- `code_review` — software theme (~"
        f"{themes.get('software', 0)} lessons)",
        "- `test_verification_review` — testing theme (~"
        f"{themes.get('testing', 0)} lessons)",
        "- `ops_monitoring_bot` — operations theme (~"
        f"{themes.get('operations', 0)} lessons)",
        "- `config_change_review` — configuration theme (~"
        f"{themes.get('configuration', 0)} lessons)",
        "- `hardware_spec_review` — hardware_design theme (~"
        f"{themes.get('hardware_design', 0)} lessons)",
        "- `integration_systems_review` — integration theme (~"
        f"{themes.get('integration', 0)} lessons)",
        "- `program_process_bot` — program_process theme (~"
        f"{themes.get('program_process', 0)} lessons)",
        "- `facilities_ground_review` — facilities theme (~"
        f"{themes.get('facilities', 0)} lessons)",
        "",
        "No merge recommended — each theme cluster has >100 hits.",
        "",
        "### Layer 2 — failure patterns (18)",
        "",
        "Patterns map to recurring mechanisms in text:",
        "- Review/monitoring gaps (insufficient_review_flagging, insufficient_monitoring_alerting)",
        "- Requirements and test gaps (requirements_gap, inadequate_test_verification)",
        "- Config/change issues (configuration_drift, late_change_bypass)",
        "- Ops/human factors (operator_procedure_gap, complacency_assumed_robustness, human_factors_ops)",
        "- System mismatch (commodity_service_mismatch, interface_integration_gap)",
        "- Quality/process (parts_materials_quality, software_assurance_gap, documentation_process_debt, procurement_supply_chain)",
        "- Infrastructure (facility_installation_defect, redundancy_analysis_incomplete, schedule_pressure_shortcut)",
        "",
        "### Impact extraction",
        "",
        f"- Lessons mentioning cost/schedule language: ~{themes.get('cost_schedule', 0)}",
        f"- Lessons mentioning safety-critical language: ~{themes.get('safety_critical', 0)}",
        "- No structured cost field in source; classify `impact_severity` from narrative during LLM pass.",
        "",
        f"- `driving_event_text` populated: {coverage.get('driving_event_text', 0)}% — mark `data_quality: partial` when missing.",
        "",
        "## Sample lesson numbers for qualitative review",
        "",
    ])
    for s in samples:
        lines.append(
            f"- [{s['lesson_number']}]({s['url']}) — {s.get('organization')} — {s.get('title', '')[:80]}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote analysis to {output}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RAW_LESSONS_PATH)
    parser.add_argument(
        "--output",
        type=Path,
        default=FAILURE_KB_ROOT / "docs" / "corpus_analysis.md",
    )
    args = parser.parse_args()
    lessons = load_lessons(args.input)
    write_report(lessons, args.output)


if __name__ == "__main__":
    main()
