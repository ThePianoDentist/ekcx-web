#!/usr/bin/env bash
# Local-only deploy helper (directory local/ is gitignored).
# Copies conf from this repo to the VPS and enables dev.ekcx.co.uk.
#
# Run from a real terminal (needed for one sudo password prompt).
set -euo pipefail

REMOTE_USER="${REMOTE_USER:-jdog}"
REMOTE_HOST="${REMOTE_HOST:-}"
REMOTE_PORT="${REMOTE_PORT:-22}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-jbknight07@gmail.com}"

if [[ -z "${REMOTE_HOST}" ]]; then
  echo "Set REMOTE_HOST, e.g.:"
  echo "  REMOTE_HOST=209.97.142.138 ./local/deploy-dev-ekcx.sh"
  exit 1
fi

REMOTE="${REMOTE_USER}@${REMOTE_HOST}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

SCP_OPTS=(-P "${REMOTE_PORT}" -o BatchMode=yes)

REMOTE_SCRIPT="$(mktemp)"
trap 'rm -f "$REMOTE_SCRIPT"' EXIT

cat >"$REMOTE_SCRIPT" <<'REMOTE_SCRIPT'
set -euo pipefail

install -o root -g root -m 0644 /tmp/dev-ekcx.service /etc/systemd/system/dev-ekcx.service
rm -f /tmp/dev-ekcx.service

mkdir -p /var/log/dev-ekcx
chown jdog:jdog /var/log/dev-ekcx

if [[ ! -d /home/jdog/ekcx-dev ]]; then
  echo "WARNING: /home/jdog/ekcx-dev does not exist — clone the repo there before starting dev-ekcx."
fi

tee /etc/nginx/sites-available/dev-ekcx-bootstrap >/dev/null <<'NGINX'
server {
    listen [::]:80;
    listen 80;
    server_name dev.ekcx.co.uk;

    location /.well-known/acme-challenge/ {
        root /usr/share/nginx/html;
    }

    location / {
        return 404;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/dev-ekcx-bootstrap /etc/nginx/sites-enabled/dev-ekcx-bootstrap
nginx -t
systemctl reload nginx

if [[ ! -d /etc/letsencrypt/live/dev.ekcx.co.uk ]]; then
  echo "==> Checking DNS for dev.ekcx.co.uk"
  if ! getent ahosts dev.ekcx.co.uk | grep -qF "${DEPLOY_VPS_IP}"; then
    echo "ERROR: dev.ekcx.co.uk must have an A record to ${DEPLOY_VPS_IP} before certbot."
    echo "Fix DNS, wait for propagation, then re-run this script."
    exit 1
  fi
  echo "==> Requesting Let's Encrypt certificate for dev.ekcx.co.uk (webroot)"
  if ! certbot certonly --webroot -w /usr/share/nginx/html \
    -d dev.ekcx.co.uk \
    --non-interactive --agree-tos -m "${CERTBOT_EMAIL}"; then
    echo "ERROR: certbot failed (often DNS or port 80). Fix and re-run this script."
    exit 1
  fi
else
  echo "==> Certificate already present at /etc/letsencrypt/live/dev.ekcx.co.uk"
fi

install -o root -g root -m 0644 /tmp/dev-ekcx /etc/nginx/sites-available/dev-ekcx
rm -f /tmp/dev-ekcx
ln -sf /etc/nginx/sites-available/dev-ekcx /etc/nginx/sites-enabled/dev-ekcx
rm -f /etc/nginx/sites-enabled/dev-ekcx-bootstrap
nginx -t
systemctl reload nginx

systemctl daemon-reload
systemctl enable dev-ekcx.service
systemctl restart dev-ekcx.service
systemctl --no-pager --full status dev-ekcx.service || true
REMOTE_SCRIPT

echo "==> Upload systemd unit"
scp "${SCP_OPTS[@]}" "${ROOT}/conf/etc/systemd/system/dev-ekcx.service" \
  "${REMOTE}:/tmp/dev-ekcx.service"

echo "==> Upload nginx site (full config; enable after certificate exists)"
scp "${SCP_OPTS[@]}" "${ROOT}/conf/etc/nginx/sites-available/dev-ekcx" \
  "${REMOTE}:/tmp/dev-ekcx"

echo "==> Upload remote setup script"
scp "${SCP_OPTS[@]}" "$REMOTE_SCRIPT" "${REMOTE}:/tmp/deploy-dev-ekcx-remote.sh"

echo "==> Run remote setup (sudo password once)"
# -tt: need a TTY for sudo; heredoc-on-stdin breaks -t, so script lives on the server.
ssh -p "${REMOTE_PORT}" -tt "${REMOTE}" \
  "sudo CERTBOT_EMAIL=$(printf '%q' "${CERTBOT_EMAIL}") DEPLOY_VPS_IP=$(printf '%q' "${REMOTE_HOST}") bash /tmp/deploy-dev-ekcx-remote.sh; rm -f /tmp/deploy-dev-ekcx-remote.sh"

echo "Done. Check https://dev.ekcx.co.uk (DNS A record must point at this host first)."