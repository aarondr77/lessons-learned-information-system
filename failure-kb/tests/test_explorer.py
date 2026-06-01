"""Tests for Dash explorer data loading."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "explorer"))

from data_loader import apply_filters, load_dataframe  # noqa: E402


def test_load_raw_dataframe():
    df, source = load_dataframe()
    assert len(df) > 2000
    assert "raw" in source or "knowledge_base" in source


def test_apply_search_filter():
    df, _ = load_dataframe()
    filtered = apply_filters(
        df,
        agents=None,
        patterns=None,
        organizations=None,
        topics=None,
        phases=None,
        confidences=None,
        impacts=None,
        date_start=None,
        date_end=None,
        search="hydrogen",
    )
    assert len(filtered) < len(df)
    assert filtered["search_text"].str.contains("hydrogen").all()
