#!/usr/bin/env python3
"""Scheduled entrypoint: tag newly-added Apple Photos. Config-driven, headless-safe.

Selects photos added since the last run (import-time watermark + lookback window,
deduped against the results ledger), exports thumbnails, classifies them with
Claude headless, auto-writes keywords, writes a date-stamped no-match report, and
advances the watermark. Designed to be launched unattended by a launchd LaunchAgent.

  python src/run.py [--config PATH] [--dry-run] [--limit N]
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import config as config_mod
import state as state_mod
import osxphotos
from export_thumbnails import best_source, make_thumbnail
from classify import build_schema, classify_one, classify_records, load_taxonomy, _result_record
from apply_keywords import apply_tags
from report import write_nomatch_report

EPOCH = datetime(1, 1, 1, tzinfo=timezone.utc)


def select_new(db, watermark, lookback_days):
    """Eligible photos (no named person, local source) added since the window start."""
    since = watermark - timedelta(days=lookback_days) if watermark else None
    out = []
    for p in db.photos():
        if not p.isphoto or p.persons:
            continue
        if since is not None and p.date_added is not None and p.date_added <= since:
            continue
        if best_source(p) is None:
            continue
        out.append(p)
    out.sort(key=lambda p: (p.date_added or EPOCH, p.uuid))
    return out


def _manifest_record(p, path):
    return {
        "uuid": p.uuid, "path": os.path.abspath(path),
        "original_name": p.original_filename,
        "date": p.date.isoformat() if p.date else None,
        "date_added": p.date_added.isoformat() if p.date_added else None,
    }


def _run(cfg, args, logger, claude_bin, started):
    watermark = state_mod.load_watermark(cfg["state_path"])
    logger.info(f"watermark={watermark} lookback={cfg['lookback_days']}d "
                f"model={cfg['model']} apply={cfg['apply_enabled'] and not args.dry_run}")

    db = osxphotos.PhotosDB(cfg["library_path"]) if cfg["library_path"] else osxphotos.PhotosDB()
    candidates = select_new(db, watermark, cfg["lookback_days"])

    done = set()
    if os.path.exists(cfg["results_path"]):
        with open(cfg["results_path"]) as f:
            done = {json.loads(line)["uuid"] for line in f if line.strip()}
    new = [p for p in candidates if p.uuid not in done]
    if args.limit:
        new = new[: args.limit]
    logger.info(f"{len(candidates)} eligible in window, {len(new)} new to process")
    if not new:
        logger.info("nothing new — done.")
        return 0

    records = []
    for p in new:
        try:
            path = make_thumbnail(p, cfg["thumbnails_dir"], cfg["thumbnail_size"])
            records.append(_manifest_record(p, path))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"thumbnail failed {p.uuid}: {e}")
    logger.info(f"exported {len(records)} thumbnails")
    if not records:
        logger.warning("no thumbnails produced — done.")
        return 0

    selectable, block = load_taxonomy(cfg["taxonomy_path"])
    selectable_set = set(selectable)
    schema_json = json.dumps(build_schema(selectable))

    canary_n = min(cfg["failfast_canary"], len(records))
    canary_results, canary_errors = [], 0
    for rec in records[:canary_n]:
        obj = classify_one(rec, block, schema_json, cfg["model"], cfg["timeout"], claude_bin)
        if "error" in obj:
            canary_errors += 1
            logger.warning(f"canary error {rec['uuid']}: {obj['error']}")
        else:
            canary_results.append(_result_record(rec, obj, selectable_set, cfg["model"]))
    if canary_n and canary_errors == canary_n:
        logger.error(f"all {canary_n} canary classifications failed — aborting "
                     f"(likely auth/systemic). Run preflight.py.")
        return 3
    with open(cfg["results_path"], "a") as f:
        for r in canary_results:
            f.write(json.dumps(r) + "\n")

    counts, rest_results = classify_records(
        records[canary_n:], cfg["results_path"], taxonomy_path=cfg["taxonomy_path"],
        model=cfg["model"], workers=cfg["workers"], timeout=cfg["timeout"],
        claude_bin=claude_bin, logger=logger)

    run_results = canary_results + rest_results
    tagged = sum(1 for r in run_results if r["tags"])
    nomatch = sum(1 for r in run_results if not r["tags"])
    errors = counts["err"] + canary_errors

    written = 0
    if cfg["apply_enabled"] and not args.dry_run:
        stats = apply_tags(run_results, osxphotos_cmd=common.osxphotos_cmd(),
                           with_parents=cfg["with_parents"],
                           min_confidence=cfg["min_confidence"], emit=logger.info)
        written = sum(stats["keywords"].values())
        if stats["errors"]:
            logger.warning(f"{stats['errors']} batch-edit chunk(s) errored")
    else:
        logger.info("apply disabled or --dry-run: keywords not written")

    report_path = os.path.join(cfg["reports_dir"], f"nomatch-{date.today().isoformat()}.md")
    write_nomatch_report(run_results, report_path,
                         title=f"No-match report {date.today().isoformat()}")

    processed = {r["uuid"] for r in run_results}
    added = [p.date_added for p in new if p.uuid in processed and p.date_added]
    if added:
        new_wm = max(added)
        if watermark is None or new_wm > watermark:
            state_mod.save_watermark(cfg["state_path"], new_wm)
            logger.info(f"watermark -> {new_wm.isoformat()}")

    dur = (datetime.now() - started).total_seconds()
    logger.info(f"SUMMARY found={len(new)} classified={len(run_results)} tagged={tagged} "
                f"no-match={nomatch} errors={errors} written={written} "
                f"report={report_path} {dur:.0f}s")
    return 0 if errors == 0 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    ap.add_argument("--dry-run", action="store_true", help="Classify but do not write keywords")
    ap.add_argument("--limit", type=int, default=0, help="Cap photos this run (0 = all)")
    args = ap.parse_args()

    cfg = config_mod.load_config(args.config)
    for d in (cfg["data_dir"], cfg["logs_dir"], cfg["reports_dir"], cfg["thumbnails_dir"]):
        os.makedirs(d, exist_ok=True)
    logger = common.setup_logging(cfg["log_path"])

    for key, val in common.load_env_file(cfg["secrets_file"]).items():
        os.environ.setdefault(key, val)

    claude_bin = common.resolve_claude(cfg["claude_bin"])
    if not claude_bin:
        logger.error(f"claude binary not found: {cfg['claude_bin']} (set claude_bin in config.json)")
        return 2

    started = datetime.now()
    try:
        with state_mod.run_lock(cfg["lock_path"]):
            return _run(cfg, args, logger, claude_bin, started)
    except state_mod.AlreadyRunning as e:
        logger.warning(f"skip: {e}")
        return 0
    except Exception as e:  # noqa: BLE001
        logger.exception(f"fatal: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
