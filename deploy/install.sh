#!/bin/bash
# Install the photo-keywords tool on this Mac: venv + deps, dirs, config, secrets
# file, and the daily LaunchAgent. Does NOT load the agent — see the printed steps.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$HERE/.venv/bin/python3"
PLIST_SRC="$HERE/deploy/com.user.photo-keywords.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.user.photo-keywords.plist"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/photo-keywords"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/photo-keywords"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/photo-keywords"

echo "==> Creating venv and installing dependencies"
python3 -m venv "$HERE/.venv"
"$HERE/.venv/bin/pip" install --quiet --upgrade pip
"$HERE/.venv/bin/pip" install --quiet -r "$HERE/requirements.txt"

echo "==> Creating per-user data/state/log directories"
mkdir -p "$CONFIG_DIR" "$DATA_DIR" "$STATE_DIR/logs"

echo "==> Seeding config.json (edit to taste)"
[ -f "$CONFIG_DIR/config.json" ] || cp "$HERE/config.example.json" "$CONFIG_DIR/config.json"

echo "==> Seeding taxonomy.json (edit to taste)"
[ -f "$CONFIG_DIR/taxonomy.json" ] || cp "$HERE/taxonomy.json" "$CONFIG_DIR/taxonomy.json"

echo "==> Preparing secrets file (chmod 600)"
touch "$CONFIG_DIR/env"
chmod 600 "$CONFIG_DIR/env"

echo "==> Writing LaunchAgent to $PLIST_DST"
mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s|__PYTHON__|$PY|g" -e "s|__PROJECT__|$HERE|g" -e "s|__HOME__|$HOME|g" \
    "$PLIST_SRC" > "$PLIST_DST"
chmod 644 "$PLIST_DST"

cat <<EOF

Installed. Finish setup manually (see INSTALL.md for detail):

  1. Grant Full Disk Access to the venv Python:
       $PY
     (System Settings > Privacy & Security > Full Disk Access)

  2. Create a headless Claude token and store it:
       claude setup-token
       echo 'CLAUDE_CODE_OAUTH_TOKEN=<paste-token>' >> $CONFIG_DIR/env

  3. Verify everything (grant Automation->Photos when prompted), repeat until all PASS:
       $PY $HERE/src/preflight.py

  4. Load the daily schedule (2:15am):
       launchctl bootstrap gui/\$(id -u) "$PLIST_DST"
       launchctl kickstart -k gui/\$(id -u)/com.user.photo-keywords   # run once now to test

EOF
