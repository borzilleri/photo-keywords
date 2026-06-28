#!/usr/bin/env python3
"""Write classified keywords back into Apple Photos (append-only).

Groups photo UUIDs by keyword and applies each with
`osxphotos batch-edit --keyword <kw> --uuid ...`. batch-edit ADDS keywords (it
does not replace), so existing keywords on each photo are preserved. Photos with
no tags are skipped.

  --with-parents     also write the parent of each nested keyword
                     (e.g. "nature/water" -> also "nature"), for broad search.
  --min-confidence   only write tags from records with confidence >= this.
  --dry-run          pass through to osxphotos batch-edit's own --dry-run.

Always run --dry-run first and eyeball the plan before a real run. A real run
can be reverted with `osxphotos batch-edit --undo`.
"""
import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict

CHUNK = 400  # uuids per batch-edit call (keeps the command line well under ARG_MAX)


def apply_tags(records, *, osxphotos_cmd=None, with_parents=False, min_confidence=0.0,
               dry_run=False, emit=None):
    """Append keywords to Photos for the given result records. Returns a stats dict."""
    osxphotos_cmd = osxphotos_cmd or ["osxphotos"]
    emit = emit or (lambda m: print(m, file=sys.stderr))

    by_keyword = defaultdict(set)
    skipped_conf = skipped_empty = 0
    for rec in records:
        if rec.get("confidence", 0.0) < min_confidence:
            skipped_conf += 1
            continue
        tags = rec.get("tags") or []
        if not tags:
            skipped_empty += 1
            continue
        for tag in tags:
            by_keyword[tag].add(rec["uuid"])
            if with_parents and "/" in tag:
                by_keyword[tag.split("/")[0]].add(rec["uuid"])

    stats = {"keywords": {}, "errors": 0,
             "skipped_empty": skipped_empty, "skipped_low_conf": skipped_conf}
    for kw in sorted(by_keyword):
        uuids = sorted(by_keyword[kw])
        stats["keywords"][kw] = len(uuids)
        for i in range(0, len(uuids), CHUNK):
            chunk = uuids[i : i + CHUNK]
            cmd = [*osxphotos_cmd, "batch-edit", "--keyword", kw]
            if dry_run:
                cmd.append("--dry-run")
            for u in chunk:
                cmd += ["--uuid", u]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                stats["errors"] += 1
                emit(f"  ! {kw} chunk {i // CHUNK}: {proc.stderr.strip()[:300]}")
            else:
                emit(f"  {kw}: chunk {i // CHUNK} ({len(chunk)}) ok")
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", default="data/results.jsonl")
    ap.add_argument("--with-parents", action="store_true",
                    help="Also write the parent of each nested keyword")
    ap.add_argument("--min-confidence", type=float, default=0.0,
                    help="Skip records below this confidence")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would change without writing (osxphotos --dry-run)")
    args = ap.parse_args()

    if not os.path.exists(args.results):
        sys.exit(f"No results file: {args.results}. Run classify.py first.")
    records = [json.loads(line) for line in open(args.results) if line.strip()]

    print(("DRY RUN — " if args.dry_run else "") + "applying ...", file=sys.stderr)
    stats = apply_tags(records, with_parents=args.with_parents,
                       min_confidence=args.min_confidence, dry_run=args.dry_run)
    written = sum(stats["keywords"].values())
    print(f"Done. keywords={len(stats['keywords'])} assignments={written} "
          f"errors={stats['errors']} skipped(no-match={stats['skipped_empty']}, "
          f"low-conf={stats['skipped_low_conf']})", file=sys.stderr)


if __name__ == "__main__":
    main()
