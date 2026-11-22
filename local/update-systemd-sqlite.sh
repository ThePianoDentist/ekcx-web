#!/usr/bin/env bash
# Point dev-ekcx and ekcx at separate SQLite files via systemd drop-ins.
# Does not replace the unit files already on the server.
#
# Run from a real terminal (one sudo password prompt):
#   REMOTE_HOST=209.97.142.138 ./local/update-systemd-sqlite.sh
set -euo pipefail

REMOTE_USER="${REMOTE_USER:-jdog}"
REMOTE_HOST="${REMOTE_HOST:-}"
REMOTE_PORT="${REMOTE_PORT:-22}"

if [[ -z "${REMOTE_HOST}" ]]; then
  echo "Set REMOTE_HOST, e.g.:"
  echo "  REMOTE_HOST=209.97.142.138 ./local/update-systemd-sqlite.sh"
  exit 1
fi

REMOTE="${REMOTE_USER}@${REMOTE_HOST}"
REMOTE_SCRIPT="$(mktemp)"
trap 'rm -f "$REMOTE_SCRIPT"' EXIT

cat >"$REMOTE_SCRIPT" <<'REMOTE_SCRIPT'
set -euo pipefail

install_sqlite_dropin() {
  local unit="$1"
  local unit_path="/etc/systemd/system/${unit}"
  if [[ ! -f "$unit_path" ]]; then
    echo "ERROR: missing ${unit_path}" >&2
    exit 1
  fi

  local wd
  wd="$(systemctl show "$unit" -p WorkingDirectory --value)"
  if [[ -z "$wd" || "$wd" == "/" ]]; then
    echo "ERROR: ${unit} has no WorkingDirectory" >&2
    exit 1
  fi

  local db="${wd}/var/ekcx.sqlite3"
  install -d -o jdog -g jdog -m 0755 "${wd}/var"

  local dropin="/etc/systemd/system/${unit}.d"
  install -d -o root -g root -m 0755 "$dropin"
  cat >"${dropin}/sqlite.conf" <<EOF
[Service]
Environment=EKCX_DB_PATH=${db}
EOF
  echo "${unit} -> ${db}"
}

install_sqlite_dropin dev-ekcx.service
install_sqlite_dropin ekcx.service

systemctl daemon-reload
systemctl restart dev-ekcx.service ekcx.service
echo
systemctl show dev-ekcx.service ekcx.service -p Id -p WorkingDirectory -p Environment --no-pager
echo
systemctl --no-pager --full status dev-ekcx.service ekcx.service || true
REMOTE_SCRIPT

echo "==> Upload drop-in installer"
scp -P "${REMOTE_PORT}" -o BatchMode=yes "$REMOTE_SCRIPT" "${REMOTE}:/tmp/update-systemd-sqlite.sh"

echo "==> Install drop-ins and restart both apps (sudo password once)"
ssh -p "${REMOTE_PORT}" -tt "${REMOTE}" \
  "sudo bash /tmp/update-systemd-sqlite.sh; rm -f /tmp/update-systemd-sqlite.sh"
