"""Shared utilities for LLIS knowledge base pipeline."""

from __future__ import annotations

import html
import re
from pathlib import Path

from bs4 import BeautifulSoup

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
FAILURE_KB_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = FAILURE_KB_ROOT / "data" / "llis"
RAW_LESSONS_PATH = DATA_DIR / "raw_lessons.jsonl"
CLASSIFIED_LESSONS_PATH = DATA_DIR / "classified_lessons.jsonl"
KNOWLEDGE_BASE_PATH = DATA_DIR / "knowledge_base.jsonl"
TAXONOMY_PATH = FAILURE_KB_ROOT / "schema" / "taxonomy.yaml"

LLIS_SEARCH_URL = "https://llis.nasa.gov/llis/lesson/_search"
LLIS_LESSON_URL = "https://llis.nasa.gov/lesson/{lesson_number}"


def strip_html(text: str | None) -> str:
    if not text or text in ("None", "null"):
        return ""
    unescaped = html.unescape(text)
    soup = BeautifulSoup(unescaped, "html.parser")
    cleaned = soup.get_text(separator=" ", strip=True)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_organization(org) -> str:
    if isinstance(org, dict):
        return (org.get("abr") or org.get("name") or "").strip()
    if isinstance(org, str):
        return org.strip()
    return ""


def normalize_topics(categories) -> list[str]:
    if not categories:
        return []
    if isinstance(categories, dict):
        names = categories.get("name", [])
        if isinstance(names, str):
            return [names.strip()] if names.strip() else []
        return [n.strip() for n in names if isinstance(n, str) and n.strip()]
    if isinstance(categories, list):
        topics: list[str] = []
        for item in categories:
            if isinstance(item, dict):
                name = item.get("name")
                if isinstance(name, str) and name.strip():
                    topics.append(name.strip())
            elif isinstance(item, str) and item.strip():
                topics.append(item.strip())
        return topics
    return []


def truncate_text(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head - 20
    return f"{text[:head]}\n...[truncated]...\n{text[-tail:]}"
