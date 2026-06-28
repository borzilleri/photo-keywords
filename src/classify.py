#!/usr/bin/env python3
"""Classify exported thumbnails with Claude Code headless (`claude -p`).

Reads the manifest, sends each thumbnail to `claude -p` with a controlled-
vocabulary prompt + JSON schema (built from taxonomy.json), and appends one
validated record per photo to results.jsonl.

  results.jsonl line: {"uuid","path","original_name","date","date_added",
                       "tags","confidence","reason","description","model"}

The taxonomy is hierarchical: the model selects the most specific CHILD keyword
(e.g. "nature/water") or a standalone keyword (e.g. "food"). Multiple tags are
allowed, and an EMPTY tag list is valid (nothing fits - do not force a guess).

Resumable: photos already present in results.jsonl are skipped. Photos that
error out are NOT written, so a re-run retries them.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TAXONOMY = os.path.join(HERE, "..", "taxonomy.json")

PROMPT_TEMPLATE = """Read the image at {image_path} and classify its CONTENT \
— what is in the image, not its composition or quality.

Use ONLY the keywords below. Do not invent keywords.

{taxonomy_block}

Rules:
- Judge the DOMINANT subject(s) of the image, not incidental background details.
- Use the most SPECIFIC keyword that applies.
- You may return MULTIPLE keywords when more than one independently dominates the
  frame (e.g. a city beside a harbor -> "urban/cityscape" and "nature/water").
- Prefer precision over coverage: a wrong keyword is worse than a missing one.
- If NO keyword fits, return an empty list. Do not force a guess.
- confidence (0.0-1.0) is your certainty. reason is ONE short sentence.
- description is a SHORT phrase naming what is in the image — at most ~12 words, not a full sentence.

Return only the structured object: tags, confidence, reason, description."""


def load_taxonomy(path):
    """Return (selectable_keywords, prompt_block) from the nested taxonomy."""
    with open(path) as f:
        data = json.load(f)
    selectable, lines, standalone = [], [], []
    lines.append("Hierarchical keywords (pick the most specific child that fits):")
    lines.append("")
    for cat in data["categories"]:
        kids = cat.get("children") or []
        if not kids:
            standalone.append(cat)
            continue
        lines.append(f"{cat['keyword']} — {cat['definition']}:")
        for c in kids:
            selectable.append(c["keyword"])
            ex = f" (NOT: {'; '.join(c['excludes'])})" if c.get("excludes") else ""
            lines.append(f"  - {c['keyword']}: {c['definition']}{ex}")
        lines.append("")
    if standalone:
        lines.append("Standalone keywords:")
        for cat in standalone:
            selectable.append(cat["keyword"])
            ex = f" (NOT: {'; '.join(cat['excludes'])})" if cat.get("excludes") else ""
            lines.append(f"  - {cat['keyword']}: {cat['definition']}{ex}")
    return selectable, "\n".join(lines)


def build_schema(selectable):
    return {
        "type": "object",
        "properties": {
            "tags": {"type": "array", "items": {"type": "string", "enum": selectable}, "minItems": 0},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reason": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["tags", "confidence", "reason", "description"],
    }


def classify_one(rec, taxonomy_block, schema_json, model, timeout,
                 claude_bin="claude", env=None):
    """Call claude -p for one photo. Returns the parsed object or {'error':...}."""
    prompt = PROMPT_TEMPLATE.format(image_path=rec["path"], taxonomy_block=taxonomy_block)
    cmd = [
        claude_bin, "-p", prompt,
        "--model", model,
        "--allowed-tools", "Read",
        "--add-dir", os.path.dirname(rec["path"]),
        "--output-format", "json",
        "--json-schema", schema_json,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        if proc.returncode != 0:
            return {"error": f"claude exit {proc.returncode}: {proc.stderr.strip()[:200]}"}
        envelope = json.loads(proc.stdout)
        if envelope.get("is_error"):
            return {"error": f"claude error: {str(envelope.get('result'))[:200]}"}
        result = envelope.get("result")
        return json.loads(result) if isinstance(result, str) else result
    except Exception as e:  # noqa: BLE001
        return {"error": f"exception: {e}"}


def _result_record(rec, obj, selectable_set, model):
    tags = [t for t in obj.get("tags", []) if t in selectable_set]
    return {
        "uuid": rec["uuid"], "path": rec["path"],
        "original_name": rec.get("original_name"), "date": rec.get("date"),
        "date_added": rec.get("date_added"), "tags": tags,
        "confidence": float(obj.get("confidence", 0.0) or 0.0),
        "reason": obj.get("reason", ""), "description": obj.get("description", ""),
        "model": model,
    }


def classify_records(records, results_path, *, taxonomy_path=DEFAULT_TAXONOMY,
                     model="sonnet", workers=3, timeout=120, claude_bin="claude",
                     env=None, dry_run=False, logger=None):
    """Classify a list of manifest records. Appends to results_path (unless dry_run).

    Returns (counts, results) where counts = {tagged, none, err} and results is the
    list of written record dicts (errored photos are skipped, not written).
    """
    selectable, taxonomy_block = load_taxonomy(taxonomy_path)
    selectable_set = set(selectable)
    schema_json = json.dumps(build_schema(selectable))

    def emit(msg):
        logger.info(msg) if logger else print(msg, file=sys.stderr)

    lock = threading.Lock()
    out = None if dry_run else open(results_path, "a")
    counts = {"tagged": 0, "none": 0, "err": 0}
    results = []

    def handle(rec):
        obj = classify_one(rec, taxonomy_block, schema_json, model, timeout, claude_bin, env)
        if "error" in obj:
            with lock:
                counts["err"] += 1
                emit(f"  ! {rec['uuid']}: {obj['error']}")
            return
        out_rec = _result_record(rec, obj, selectable_set, model)
        with lock:
            counts["tagged" if out_rec["tags"] else "none"] += 1
            results.append(out_rec)
            if out is not None:
                out.write(json.dumps(out_rec) + "\n")
                out.flush()
            done = sum(counts.values())
            if done % 25 == 0:
                emit(f"  ... {done}/{len(records)}  tagged={counts['tagged']} "
                     f"none={counts['none']} err={counts['err']}")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(handle, r) for r in records]
        for fut in as_completed(futures):
            fut.result()
    if out:
        out.close()
    return counts, results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default="data/manifest.jsonl")
    ap.add_argument("--results", default="data/results.jsonl")
    ap.add_argument("--taxonomy", default=DEFAULT_TAXONOMY)
    ap.add_argument("--model", default="sonnet", help="sonnet | haiku | opus | full id")
    ap.add_argument("--workers", type=int, default=3, help="Parallel claude calls")
    ap.add_argument("--timeout", type=int, default=120, help="Per-image timeout (s)")
    ap.add_argument("--limit", type=int, default=0, help="Cap photos this run (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="Print results, do not write")
    args = ap.parse_args()

    with open(args.manifest) as f:
        manifest = [json.loads(line) for line in f if line.strip()]
    if not manifest:
        sys.exit("Empty manifest. Run export_thumbnails.py first.")

    done = set()
    if os.path.exists(args.results):
        with open(args.results) as f:
            done = {json.loads(line)["uuid"] for line in f if line.strip()}
    todo = [r for r in manifest if r["uuid"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(todo)} to classify ({len(done)} already done), model={args.model}, "
          f"workers={args.workers}", file=sys.stderr)

    counts, _ = classify_records(
        todo, args.results, taxonomy_path=args.taxonomy, model=args.model,
        workers=args.workers, timeout=args.timeout, dry_run=args.dry_run)
    print(f"Done. tagged={counts['tagged']} no-match={counts['none']} errors={counts['err']}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
