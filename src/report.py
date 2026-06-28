#!/usr/bin/env python3
"""Report on classified photos that matched NO keyword.

Reads results.jsonl and writes a Markdown table of every photo with an empty
tag list: filename, date/time, and the model's brief description. Useful for
spotting taxonomy gaps (categories worth adding).

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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", default="data/results.jsonl")
    ap.add_argument("--out", default="data/nomatch-report.md")
    args = ap.parse_args()

    if not os.path.exists(args.results):
        sys.exit(f"No results file: {args.results}. Run classify.py first.")

    rows = []
    total = 0
    with open(args.results) as f:
        for line in f:
            if not line.strip():
                continue
            total += 1
            rec = json.loads(line)
            if not rec.get("tags"):
                rows.append(rec)
    rows.sort(key=lambda r: r.get("date") or "")

    lines = [
        f"# No-match report",
        "",
        f"{len(rows)} of {total} classified photos matched no keyword.",
        "",
        "| Filename | Date/Time | Description |",
        "| --- | --- | --- |",
    ]
    for r in rows:
        name = (r.get("original_name") or r["uuid"]).replace("|", "\\|")
        desc = (r.get("description") or r.get("reason") or "").replace("|", "\\|").strip()
        lines.append(f"| {name} | {fmt_date(r.get('date'))} | {desc} |")
    report = "\n".join(lines) + "\n"

    with open(args.out, "w") as f:
        f.write(report)
    print(report)
    print(f"Wrote {args.out} ({len(rows)} no-match photos)", file=sys.stderr)


if __name__ == "__main__":
    main()
