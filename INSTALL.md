# Install & schedule photo-keywords (target Mac)

Sets up the tool to **tag newly-added Apple Photos daily, unattended**, via a launchd
LaunchAgent. You run these steps once on the target Mac; they require an active login session.

## Prerequisites

- macOS with the **Apple Photos** library you want tagged (signed in).
- **Python 3.11+** (`python3`).
- **Claude Code CLI** installed and working (`claude --version`), on a subscription that allows
  `claude setup-token` (see step 3 — this is the one thing to confirm up front).

## Steps

### 1. Copy the project and run the installer
```bash
# place the photo-keywords/ folder somewhere stable, e.g. ~/photo-keywords
cd ~/photo-keywords
bash deploy/install.sh
```
This creates `.venv`, installs pinned deps, makes `data/ logs/ reports/`, seeds `config.json`
from the example, creates the chmod-600 secrets file, and writes the LaunchAgent plist. It does
**not** load the schedule yet.

### 2. Grant Full Disk Access
Give **Full Disk Access** to the venv Python (the installer prints its exact path):
```
<project>/.venv/bin/python3
```
System Settings → Privacy & Security → Full Disk Access → add that binary.
> If you later upgrade Python, the path/identity can change and FDA must be re-granted.

### 3. Create the headless Claude token
launchd can't use your interactive login keychain, so the job needs a long-lived token:
```bash
claude setup-token
echo 'CLAUDE_CODE_OAUTH_TOKEN=<paste-token>' >> ~/.config/photo-keywords/env
```
> If your org/SSO blocks `setup-token`, headless classification isn't possible without an API
> key — stop here and revisit (see "Fallback" below).

### 4. Verify with preflight (the doctor)
```bash
.venv/bin/python3 src/preflight.py
```
Runs ordered checks and prints PASS / WARN / FAIL with remediation. The first run triggers the
macOS **Photos** and **Automation** prompts — allow them. Re-run until all checks PASS (a token
WARN must become PASS for headless use).

### 5. Configure and load the schedule
Edit `config.json` if desired (model, workers, cadence is in the plist), then:
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.photo-keywords.plist
launchctl kickstart -k gui/$(id -u)/com.user.photo-keywords   # run once now to test
```
The **first run is a full backfill** of the existing library (can take a while); subsequent daily
runs only process newly-added photos.

## Configuration (`config.json`)

| key | default | meaning |
|-----|---------|---------|
| `model` | `sonnet` | classification model (`haiku` cheaper, `opus` for hard cases) |
| `workers` | `4` | parallel `claude -p` calls |
| `lookback_days` | `7` | re-scan window so not-yet-downloaded iCloud photos get retried |
| `min_confidence` | `0.0` | only write tags at/above this confidence |
| `with_parents` | `false` | also write the bare parent keyword (`nature` alongside `nature/water`) |
| `apply_enabled` | `true` | write keywords to Photos (set `false` for classify-only) |
| `claude_bin` | `claude` | path/name of the claude binary |
| `secrets_file` | `~/.config/photo-keywords/env` | where `CLAUDE_CODE_OAUTH_TOKEN` lives |

Change the run time by editing `StartCalendarInterval` in the installed plist, then re-`bootstrap`.

## Where things land

- **Logs:** `logs/photo-keywords.log` (rotating) and `logs/launchd.{out,err}.log`.
- **No-match reports:** `reports/nomatch-YYYY-MM-DD.md` — one per run; review and delete as you like.
- **State/ledger:** `data/state.json` (watermark), `data/results.jsonl` (every classified photo).

## Operating

- **Run manually:** `.venv/bin/python3 src/run.py` (add `--dry-run` to classify without writing,
  `--limit N` to cap).
- **Undo a write:** `.venv/bin/python3 -m osxphotos batch-edit --undo`.
- **Unload schedule:** `launchctl bootout gui/$(id -u)/com.user.photo-keywords`.
- **Re-scan from scratch:** delete `data/state.json` (re-processes via the ledger; already-tagged
  photos are skipped because their UUIDs are in `results.jsonl`).

## Notes & limits

- The job only runs while you're **logged in** (LaunchAgent, not a system daemon — Photos is
  TCC-protected and needs your GUI session).
- Photos with a **named person are excluded** entirely; videos are skipped.
- Keyword writes are **append-only** (existing keywords preserved) and go through AppleScript
  (the only way Apple Photos allows keyword editing) — hence the Automation→Photos requirement.
- **Fallback if headless auth/write is blocked:** set `apply_enabled: false` to classify-only and
  review `reports/` + `results.jsonl`, then run `src/apply_keywords.py` manually when logged in.
