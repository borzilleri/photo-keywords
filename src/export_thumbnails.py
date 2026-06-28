#!/usr/bin/env python3
"""Export resized thumbnails from Apple Photos for classification.

Filters OUT any photo that has a named/identified person, plus videos. For each
remaining photo it picks the best LOCAL source and downscales it with `sips`:

  - if the original is on disk, use it (sips also converts HEIC -> JPEG);
  - otherwise use the largest locally-cached preview/derivative.

This means offloaded photos (iCloud "Optimize Mac Storage") are still handled
WITHOUT downloading originals — the local preview is plenty for content
classification. Originals are read-only; nothing in Photos is modified.

Outputs:
  <output>/{uuid}.jpg          one thumbnail per eligible photo
  <manifest>                   JSONL: {"uuid","path","original_name","date"}

Idempotent: photos whose thumbnail already exists are skipped.
"""
import argparse
import json
import os
import random
import subprocess
import sys

import osxphotos


def best_source(p):
    """Path to the best LOCAL image for this photo, or None if unavailable."""
    if p.path and os.path.exists(p.path):
        return p.path
    derivs = [d for d in (p.path_derivatives or []) if d and os.path.exists(d)]
    if derivs:
        return max(derivs, key=os.path.getsize)  # largest = highest resolution
    return None


def eligible_photos(db):
    """Photos with no identified person and a usable local source."""
    out = []
    for p in db.photos():
        if not p.isphoto:            # skip videos
            continue
        if p.persons:                # named/identified person -> exclude entirely
            continue
        if best_source(p) is None:   # nothing local to classify
            continue
        out.append(p)
    out.sort(key=lambda p: (p.date, p.uuid))  # deterministic --limit
    return out


def make_thumbnail(photo, out_dir, size):
    """Downscale the best local source to {uuid}.jpg. Returns the path."""
    dst = os.path.join(out_dir, f"{photo.uuid}.jpg")
    if os.path.exists(dst):
        return dst
    src = best_source(photo)
    if not src:
        raise RuntimeError("no local source")
    subprocess.run(
        ["sips", "-s", "format", "jpeg", "-Z", str(size), src, "--out", dst],
        check=True, capture_output=True,
    )
    return dst


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--library", help="Path to .photoslibrary (default: system library)")
    ap.add_argument("--output", default="data/thumbnails", help="Thumbnail output dir")
    ap.add_argument("--manifest", default="data/manifest.jsonl")
    ap.add_argument("--size", type=int, default=1024, help="Max dimension in px")
    ap.add_argument("--limit", type=int, default=0, help="Cap photos (0 = all)")
    ap.add_argument("--shuffle", action="store_true",
                    help="Randomize order before --limit (representative sample)")
    ap.add_argument("--seed", type=int, default=0, help="Seed for --shuffle (reproducible)")
    args = ap.parse_args()

    os.makedirs(args.output, exist_ok=True)
    os.makedirs(os.path.dirname(args.manifest) or ".", exist_ok=True)

    print("Reading Photos library ...", file=sys.stderr)
    db = osxphotos.PhotosDB(args.library) if args.library else osxphotos.PhotosDB()
    photos = eligible_photos(db)
    if args.shuffle:
        random.Random(args.seed).shuffle(photos)
    if args.limit:
        photos = photos[: args.limit]
    print(f"{len(photos)} eligible photos (no named person, local source).", file=sys.stderr)

    records, made, skipped, failed = [], 0, 0, 0
    for i, p in enumerate(photos, 1):
        try:
            existed = os.path.exists(os.path.join(args.output, f"{p.uuid}.jpg"))
            path = make_thumbnail(p, args.output, args.size)
            made += 0 if existed else 1
            skipped += 1 if existed else 0
            records.append({
                "uuid": p.uuid,
                "path": os.path.abspath(path),
                "original_name": p.original_filename,
                "date": p.date.isoformat() if p.date else None,
            })
        except Exception as e:  # noqa: BLE001 - keep going, report at end
            failed += 1
            print(f"  ! {p.uuid}: {e}", file=sys.stderr)
        if i % 50 == 0:
            print(f"  ... {i}/{len(photos)}", file=sys.stderr)

    with open(args.manifest, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    print(f"Done. exported={made} reused={skipped} failed={failed}", file=sys.stderr)
    print(f"Manifest: {args.manifest} ({len(records)} entries)", file=sys.stderr)


if __name__ == "__main__":
    main()
