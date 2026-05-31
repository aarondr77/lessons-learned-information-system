# NASA LLIS Failure Knowledge Base

Agent-oriented knowledge base built from NASA Lessons Learned Information System (LLIS) data.

## Pipeline

1. **Export** — `python failure-kb/scripts/export_llis.py`
2. **Analyze** — `python failure-kb/scripts/analyze_corpus.py`
3. **Classify** — `python failure-kb/scripts/classify_lessons.py --resume`
4. **Build KB** — `python failure-kb/scripts/build_knowledge_base.py`
5. **Explore** — `streamlit run failure-kb/explorer/app.py`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r failure-kb/requirements.txt
```

Add `ANTHROPIC_API_KEY` to workspace root `.env`.

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

## Validation

```bash
pytest failure-kb/tests/
python failure-kb/scripts/report_distribution.py
```
