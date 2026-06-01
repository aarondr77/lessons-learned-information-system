"""Load and filter LLIS knowledge base data for the Dash explorer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import yaml

EXPLORER_ROOT = Path(__file__).resolve().parent
FAILURE_KB_ROOT = EXPLORER_ROOT.parent
sys.path.insert(0, str(FAILURE_KB_ROOT / "scripts"))

from utils import (  # noqa: E402
    CLASSIFIED_LESSONS_PATH,
    KNOWLEDGE_BASE_PATH,
    RAW_LESSONS_PATH,
    TAXONOMY_PATH,
)


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


def load_taxonomy_labels() -> tuple[dict[str, str], dict[str, str]]:
    if not TAXONOMY_PATH.exists():
        return {}, {}
    with TAXONOMY_PATH.open(encoding="utf-8") as f:
        tax = yaml.safe_load(f)
    agents = {k: v.get("label", k) for k, v in tax.get("agents", {}).items()}
    patterns = {k: v.get("label", k) for k, v in tax.get("failure_patterns", {}).items()}
    return agents, patterns


def load_dataframe() -> tuple[pd.DataFrame, str]:
    """Return (dataframe, source_description)."""
    if KNOWLEDGE_BASE_PATH.exists():
        rows = load_jsonl(KNOWLEDGE_BASE_PATH)
        source = str(KNOWLEDGE_BASE_PATH.name)
    elif CLASSIFIED_LESSONS_PATH.exists():
        raw_by_id = {r["lesson_number"]: r for r in load_jsonl(RAW_LESSONS_PATH)}
        rows = []
        for c in load_jsonl(CLASSIFIED_LESSONS_PATH):
            rows.append({**raw_by_id.get(c["lesson_number"], {}), **c})
        source = "classified_lessons.jsonl + raw_lessons.jsonl"
    else:
        rows = load_jsonl(RAW_LESSONS_PATH)
        source = "raw_lessons.jsonl (not yet classified)"

    if not rows:
        return pd.DataFrame(), "no data"

    df = pd.DataFrame(rows)
    df["lesson_date"] = pd.to_datetime(df.get("lesson_date"), errors="coerce")
    df["year"] = df["lesson_date"].dt.year

    for col in ("secondary_agents", "failure_patterns", "nasa_topics", "evidence"):
        if col not in df.columns:
            df[col] = [[] for _ in range(len(df))]
        df[col] = df[col].apply(lambda x: x if isinstance(x, list) else [])

    for col in ("primary_agent", "confidence", "impact_severity", "impact_notes"):
        if col not in df.columns:
            df[col] = None

    df["search_text"] = (
        df.get("title", pd.Series(dtype=str)).fillna("")
        + " "
        + df.get("abstract_text", pd.Series(dtype=str)).fillna("")
        + " "
        + df.get("lesson_text", pd.Series(dtype=str)).fillna("")
    ).str.lower()

    return df, source


def apply_filters(
    df: pd.DataFrame,
    agents: list[str] | None,
    patterns: list[str] | None,
    organizations: list[str] | None,
    topics: list[str] | None,
    phases: list[str] | None,
    confidences: list[str] | None,
    impacts: list[str] | None,
    date_start: str | None,
    date_end: str | None,
    search: str | None,
) -> pd.DataFrame:
    if df.empty:
        return df

    out = df.copy()

    if agents:
        out = out[
            out["primary_agent"].isin(agents)
            | out["secondary_agents"].apply(lambda xs: bool(set(xs) & set(agents)))
        ]

    if patterns:
        out = out[out["failure_patterns"].apply(lambda xs: bool(set(xs) & set(patterns)))]

    if organizations:
        out = out[out["organization"].isin(organizations)]

    if topics:
        out = out[out["nasa_topics"].apply(lambda xs: bool(set(xs) & set(topics)))]

    if phases:
        out = out[out["program_phase"].fillna("").isin(phases)]

    if confidences:
        out = out[out["confidence"].isin(confidences)]

    if impacts:
        out = out[out["impact_severity"].isin(impacts)]

    if date_start:
        out = out[out["lesson_date"] >= pd.to_datetime(date_start)]

    if date_end:
        out = out[out["lesson_date"] <= pd.to_datetime(date_end)]

    if search:
        q = search.lower().strip()
        out = out[out["search_text"].str.contains(q, na=False)]

    return out


def pattern_agent_matrix(df: pd.DataFrame, top_patterns: int = 12) -> pd.DataFrame:
    if df.empty or "primary_agent" not in df.columns:
        return pd.DataFrame()

    pattern_counts: dict[str, int] = {}
    for patterns in df["failure_patterns"]:
        for p in patterns:
            pattern_counts[p] = pattern_counts.get(p, 0) + 1

    top = sorted(pattern_counts, key=pattern_counts.get, reverse=True)[:top_patterns]
    agents = sorted(df["primary_agent"].dropna().unique())

    matrix = pd.DataFrame(0, index=top, columns=agents)
    for _, row in df.iterrows():
        agent = row.get("primary_agent")
        if not agent or agent not in matrix.columns:
            continue
        for p in row.get("failure_patterns", []):
            if p in matrix.index:
                matrix.loc[p, agent] += 1
    return matrix


def explode_for_export(df: pd.DataFrame) -> pd.DataFrame:
    export = df.copy()
    for col in ("secondary_agents", "failure_patterns", "nasa_topics"):
        if col in export.columns:
            export[col] = export[col].apply(lambda xs: "; ".join(xs) if xs else "")
    if "evidence" in export.columns:
        export["evidence"] = export["evidence"].apply(
            lambda xs: " | ".join(e.get("quote", "") for e in xs) if xs else ""
        )
    drop_cols = [c for c in ("search_text", "year") if c in export.columns]
    return export.drop(columns=drop_cols, errors="ignore")
