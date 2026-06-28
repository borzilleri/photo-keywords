#!/usr/bin/env python3
"""Report on classified photos that matched NO keyword.

Writes a Markdown table of every photo with an empty tag list: filename,
date/time, and the model's brief description. Useful for spotting taxonomy gaps.

  python src/report.py                 # -> data/nomatch-report.md (and stdout)
  python src/report.py --out report.md
"""
import argparse
import json
import os
import sys
from datetime import datetime


def fmt_date(iso):
    if not iso:
        return "?"
    try:
        return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso


def write_nomatch_report(records, out_path, title="No-match report"):
    """Write a Markdown no-match report for `records`; return the no-match count."""
    rows = [r for r in records if not r.get("tags")]
    rows.sort(key=lambda r: r.get("date") or "")
    lines = [
        f"# {title}",
        "",
        f"{len(rows)} of {len(records)} classified photos matched no keyword.",
        "",
        "| Filename | Date/Time | Description |",
        "| --- | --- | --- |",
    ]
    for r in rows:
        name = (r.get("original_name") or r["uuid"]).replace("|", "\\|")
        desc = (r.get("description") or r.get("reason") or "").replace("|", "\\|").strip()
        lines.append(f"| {name} | {fmt_date(r.get('date'))} | {desc} |")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", default="data/results.jsonl")
    ap.add_argument("--out", default="data/nomatch-report.md")
    args = ap.parse_args()

    if not os.path.exists(args.results):
        sys.exit(f"No results file: {args.results}. Run classify.py first.")
    records = [json.loads(line) for line in open(args.results) if line.strip()]
    n = write_nomatch_report(records, args.out)
    print(open(args.out).read())
    print(f"Wrote {args.out} ({n} no-match photos)", file=sys.stderr)


if __name__ == "__main__":
    main()
