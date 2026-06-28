#!/usr/bin/env python3
"""Doctor: verify the access, binaries, and auth the scheduled job needs.

Runs ordered checks and prints PASS / WARN / FAIL with remediation. Exits
nonzero if any hard check FAILs. Run during install and whenever something
looks off:

  python src/preflight.py
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import config as config_mod

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def _claude_test(claude_bin, env):
    """Make a tiny live claude -p call. Returns (ok, detail)."""
    cmd = [claude_bin, "-p", "Reply with exactly: ok", "--output-format", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90, env=env)
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:160]
    if proc.returncode != 0:
        return False, f"exit {proc.returncode}: {proc.stderr.strip()[:160]}"
    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False, "unparseable claude output"
    if envelope.get("is_error"):
        return False, str(envelope.get("result"))[:160]
    return True, str(envelope.get("result")).strip()[:60]


def run_checks():
    cfg = config_mod.load_config()
    secrets = common.load_env_file(cfg["secrets_file"])
    checks = []

    checks.append(("config", PASS, f"loaded; data_dir={cfg['data_dir']}"))

    claude_bin = common.resolve_claude(cfg["claude_bin"])
    checks.append(("claude binary", PASS if claude_bin else FAIL,
                   claude_bin or f"not found: '{cfg['claude_bin']}' — set claude_bin in config.json"))
    sips_ok = os.path.exists("/usr/bin/sips")
    checks.append(("sips", PASS if sips_ok else FAIL, "/usr/bin/sips" if sips_ok else "missing"))
    try:
        v = subprocess.run([*common.osxphotos_cmd(), "--version"],
                           capture_output=True, text=True, timeout=60)
        out = (v.stdout or v.stderr).strip()
        ox_ok, ox_detail = v.returncode == 0, (out.splitlines()[0] if out else "")
    except Exception as e:  # noqa: BLE001
        ox_ok, ox_detail = False, str(e)
    checks.append(("osxphotos", PASS if ox_ok else FAIL, ox_detail[:80]))

    sample_uuid = None
    try:
        import osxphotos
        db = osxphotos.PhotosDB(cfg["library_path"]) if cfg["library_path"] else osxphotos.PhotosDB()
        photos = db.photos()
        sample_uuid = next((p.uuid for p in photos), None)
        checks.append(("Full Disk Access (read Photos)", PASS, f"{len(photos)} assets readable"))
    except Exception as e:  # noqa: BLE001
        checks.append(("Full Disk Access (read Photos)", FAIL,
                       f"{type(e).__name__}: {str(e)[:60]} — grant Full Disk Access to "
                       f"{sys.executable} (System Settings > Privacy & Security)"))

    if sample_uuid:
        cmd = [*common.osxphotos_cmd(), "batch-edit", "--dry-run",
               "--keyword", "__preflight__", "--uuid", sample_uuid]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0:
                checks.append(("Automation -> Photos (write)", PASS, "batch-edit dry-run ok"))
            else:
                checks.append(("Automation -> Photos (write)", FAIL,
                               proc.stderr.strip()[:100] + " — allow Automation control of Photos"))
        except Exception as e:  # noqa: BLE001
            checks.append(("Automation -> Photos (write)", FAIL, str(e)[:100]))
    else:
        checks.append(("Automation -> Photos (write)", WARN, "no sample photo to test"))

    token = secrets.get("CLAUDE_CODE_OAUTH_TOKEN") or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if not claude_bin:
        checks.append(("Claude auth", FAIL, "claude binary not found"))
    else:
        ok, detail = _claude_test(claude_bin, {**os.environ, **secrets})
        if ok and token:
            checks.append(("Claude auth", PASS, f"token present; test call ok ({detail})"))
        elif ok:
            checks.append(("Claude auth", WARN,
                           "test call ok via interactive login, but NO CLAUDE_CODE_OAUTH_TOKEN — "
                           f"headless runs will fail. Run `claude setup-token`, add it to {cfg['secrets_file']}"))
        else:
            checks.append(("Claude auth", FAIL, f"test call failed: {detail}"))
    return checks


def main():
    checks = run_checks()
    width = max(len(name) for name, _, _ in checks)
    print()
    for name, status, detail in checks:
        print(f"  [{status}] {name.ljust(width)}  {detail}")
    fails = sum(1 for _, s, _ in checks if s == FAIL)
    warns = sum(1 for _, s, _ in checks if s == WARN)
    print(f"\n{len(checks)} checks: {len(checks) - fails - warns} pass, {warns} warn, {fails} fail\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
