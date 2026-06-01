# NASA LLIS Failure Knowledge Base

Agent-oriented knowledge base built from NASA Lessons Learned Information System (LLIS) data.

## Pipeline

1. **Export** — `python failure-kb/scripts/export_llis.py`
2. **Analyze** — `python failure-kb/scripts/analyze_corpus.py`
3. **Classify** — `python failure-kb/scripts/classify_lessons.py --resume`
4. **Build KB** — `python failure-kb/scripts/build_knowledge_base.py`
5. **Explore** — `python failure-kb/explorer/app.py` (Dash UI at http://127.0.0.1:8050)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r failure-kb/requirements.txt
```

Add `ANTHROPIC_API_KEY` to workspace root `.env`. Classification uses **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) by default; override with `ANTHROPIC_MODEL` in `.env`.

## Taxonomy

Two-layer classification (see [`schema/taxonomy.yaml`](schema/taxonomy.yaml)):

- **Layer 1 — Lifecycle agents:** Where intervention would have prevented the incident (e.g. `design_safety_review`, `ops_monitoring_bot`)
- **Layer 2 — Failure patterns:** Multi-label root-cause tags (e.g. `insufficient_review_flagging`, `commodity_service_mismatch`)

Derived from corpus analysis in [`docs/corpus_analysis.md`](docs/corpus_analysis.md).

## Data

| File | Description |
| --- | --- |
| `data/llis/raw_lessons.jsonl` | Exported + normalized lessons (~2106 valid records) |
| `data/llis/classified_lessons.jsonl` | LLM classification output |
| `data/llis/knowledge_base.jsonl` | Merged raw + classified |
| `agents/*/corpus.jsonl` | Per-agent training slices |

## Explorer (Dash)

Interactive dashboard at `failure-kb/explorer/`:

| Tab | Features |
| --- | --- |
| **Dashboard** | KPI cards, agent/pattern/org charts, timeline |
| **Top issues** | Pattern frequency, pattern×agent heatmap, high-impact list |
| **Browse lessons** | Filterable table, lesson detail panel, CSV export |

```bash
python failure-kb/explorer/app.py
# open http://127.0.0.1:8050
```

Works on raw data before classification (with a warning banner). Full analytics appear after `build_knowledge_base.py`.

## Validation

```bash
pytest failure-kb/tests/
python failure-kb/scripts/report_distribution.py
```
