# AGENTS.md

## Cursor Cloud specific instructions

### Product

Single Python data pipeline under `failure-kb/`: NASA LLIS export → corpus analysis → Anthropic classification → knowledge base merge and per-agent `corpus.jsonl` slices. See `failure-kb/README.md` for the full pipeline.

### Environment

- **Python 3.12+** with a project venv at `/workspace/.venv` (gitignored).
- **System package (one-time on fresh Ubuntu VMs):** if `python3 -m venv .venv` fails with “ensurepip is not available”, install `python3.12-venv` via apt before creating the venv.
- **Secrets:** `ANTHROPIC_API_KEY` in `/workspace/.env` (loaded by `classify_lessons.py` via `python-dotenv`). Optional: `ANTHROPIC_MODEL`.

Activate the venv for all commands:

```bash
source /workspace/.venv/bin/activate
```

### Common commands

| Task | Command |
|------|---------|
| Install deps | `pip install -r failure-kb/requirements.txt` (inside venv) |
| Corpus analysis | `python failure-kb/scripts/analyze_corpus.py` |
| Classify (API) | `python failure-kb/scripts/classify_lessons.py --resume` (or `--pilot`, `--limit N`) |
| Build KB | `python failure-kb/scripts/build_knowledge_base.py` |
| Distribution report | `python failure-kb/scripts/report_distribution.py` |
| Export from NASA | `python failure-kb/scripts/export_llis.py` (full export; needs outbound HTTPS) |

There is **no** committed linter config, Makefile, or `failure-kb/tests/` directory (pytest is listed in requirements but tests are not in the repo). `failure-kb/explorer/app.py` (Streamlit) is documented but not present.

### Validation without full re-classify

Use committed `raw_lessons.jsonl` and `classified_lessons.jsonl`:

```bash
python failure-kb/scripts/build_knowledge_base.py
python failure-kb/scripts/report_distribution.py
```

`report_distribution.py` exits **1** when any primary agent has fewer than 20 lessons (expected with the small 28-lesson pilot sample).

### Services

No Docker or long-running servers. External dependencies: NASA LLIS HTTPS API and Anthropic API for export/classify steps only.
