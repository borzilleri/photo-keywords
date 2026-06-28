#!/usr/bin/env python3
"""Write classified keywords back into Apple Photos (append-only).

Reads results.jsonl, groups photo UUIDs by keyword, and applies each keyword
with `osxphotos batch-edit --keyword <kw> --uuid ...`. batch-edit ADDS keywords
(it does not replace), so existing keywords on each photo are preserved. Photos
with no tags are skipped.

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

    by_keyword = defaultdict(set)
    skipped_conf = skipped_empty = 0
    with open(args.results) as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("confidence", 0.0) < args.min_confidence:
                skipped_conf += 1
                continue
            tags = rec.get("tags", [])
            if not tags:
                skipped_empty += 1
                continue
            for tag in tags:
                by_keyword[tag].add(rec["uuid"])
                if args.with_parents and "/" in tag:
                    by_keyword[tag.split("/")[0]].add(rec["uuid"])

    if not by_keyword:
        sys.exit("Nothing to apply.")

    print(f"Plan (skipped: {skipped_empty} no-match, {skipped_conf} low-confidence):", file=sys.stderr)
    for kw in sorted(by_keyword):
        print(f"  {kw}: {len(by_keyword[kw])} photos", file=sys.stderr)
    print(("DRY RUN — " if args.dry_run else "") + "applying ...", file=sys.stderr)

    for kw in sorted(by_keyword):
        uuids = sorted(by_keyword[kw])
        for i in range(0, len(uuids), CHUNK):
            chunk = uuids[i : i + CHUNK]
            # batch-edit operates on the default system Photos library.
            cmd = ["osxphotos", "batch-edit", "--keyword", kw]
            if args.dry_run:
                cmd.append("--dry-run")
            for u in chunk:
                cmd += ["--uuid", u]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                print(f"  ! {kw} chunk {i // CHUNK}: {proc.stderr.strip()[:300]}", file=sys.stderr)
            else:
                print(f"  {kw}: chunk {i // CHUNK} ({len(chunk)}) ok", file=sys.stderr)

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
