# photo-keywords

Automatically tag an Apple Photos library with **content keywords** (nature, urban, food, …)
using Claude Code headless for vision. No API key required — `claude -p` uses your existing
Claude auth.

Photos containing a **named/identified person are excluded** from the entire pipeline.
Keyword writes are **append-only** — existing keywords are never removed.

## Pipeline

```
export_thumbnails.py  →  data/thumbnails/{uuid}.jpg + data/manifest.jsonl
classify.py           →  data/results.jsonl   (claude -p per image)
apply_keywords.py     →  keywords written into Apple Photos (append-only)
```

## Setup

```bash
cd photo-keywords
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### macOS permissions (most common first-run snag)

Grant these to the app running the scripts (Terminal / iTerm), in System Settings → Privacy & Security:

- **Full Disk Access** — so `osxphotos` can read the library and export originals.
- **Photos** — library access.
- **Automation → Photos** — only needed for the `photoscript` fallback writer.

`claude` must be installed and logged in (the same auth you use interactively).

## Run order

```bash
# 0. activate venv
source .venv/bin/activate

# 1. TEST BATCH — export a representative random sample, no named person
python src/export_thumbnails.py --shuffle --limit 100

# 2. classify the test batch (writes data/results.jsonl, resumable)
python src/classify.py

# 3. review data/results.jsonl; refine taxonomy.json + docs/keywords.md until
#    the tags look right (clear results.jsonl and re-run to re-test)
#    optional: report photos that matched no keyword (spots taxonomy gaps)
python src/report.py

# 4. preview the write-back, then apply (append-only; --undo available)
python src/apply_keywords.py --dry-run
python src/apply_keywords.py
```

### Full library

Drop `--limit` from the export step to process everything. `classify.py` and
`apply_keywords.py` always operate on whatever is in the manifest/results, and both are
resumable/idempotent, so you can stop and restart safely.

## Tuning

- **Taxonomy** is `taxonomy.json` (canonical) mirrored by `docs/keywords.md`. It is nested
  (`nature/water`, `art/anime`, …); the classifier picks the most specific child, may return
  multiple, or none. How to write good descriptions: `docs/writing-keyword-descriptions.md`.
- **Prompt & invocation**: `docs/prompts.md`.
- **Model**: `classify.py --model haiku` (cheaper/faster) or `--model opus` (hardest cases);
  default `sonnet`.
- **Confidence**: recorded per photo. Write only high-confidence tags with
  `apply_keywords.py --min-confidence 0.7`.
- **Parent keywords**: `apply_keywords.py --with-parents` also writes the bare parent
  (`nature/water` → also `nature`) for broad searches.
- **Speed**: `classify.py --workers N` runs N `claude -p` calls in parallel.
- **Sampling**: `export_thumbnails.py --shuffle [--seed N]` for a representative random subset.

## Files

| Path | Purpose |
|------|---------|
| `taxonomy.json` | Canonical keyword vocabulary + descriptions (single source of truth) |
| `docs/writing-keyword-descriptions.md` | Guide: how to write reliable keyword descriptions |
| `docs/keywords.md` | Human-readable taxonomy |
| `docs/prompts.md` | Classification prompt + `claude -p` invocation |
| `src/export_thumbnails.py` | Export + person-filter + resize |
| `src/classify.py` | Classify via `claude -p`, write `results.jsonl` |
| `src/apply_keywords.py` | Append keywords into Photos via `osxphotos batch-edit` |
| `src/report.py` | Markdown report of photos that matched no keyword |
| `data/` | Generated: thumbnails, manifest, results, reports |
