#!/usr/bin/env bash
# One-time bootstrap for GitHub Actions VPS deploy (issue #34):
#   (1) Actions SSH key → authorized_keys + repo secrets
#   (3) Scoped sudoers for systemctl restart
#
# Run from a real terminal (sudo password on VPS for sudoers step).
# Does not configure the on-VPS git deploy key (see docs/deploy.md).
#
#   REMOTE_HOST=209.97.142.138 ./local/setup-github-actions-deploy.sh
#   ./local/setup-github-actions-deploy.sh --sudoers-only   # skip keys/secrets
#   ./local/setup-github-actions-deploy.sh --secrets-only   # skip sudoers
set -euo pipefail

REMOTE_USER="${REMOTE_USER:-jdog}"
REMOTE_HOST="${REMOTE_HOST:-}"
REMOTE_PORT="${REMOTE_PORT:-22}"
KEY_COMMENT="github-actions-ekcx-deploy"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEY_PATH="${ROOT}/local/github-actions-deploy"
SUDOERS_SRC="${ROOT}/conf/etc/sudoers.d/ekcx-deploy"

do_secrets=1
do_sudoers=1

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  echo
  echo "Options:"
  echo "  --secrets-only   Keys, authorized_keys, gh secrets (skip sudoers)"
  echo "  --sudoers-only   Install ekcx-deploy sudoers (skip secrets)"
  echo "  --regenerate-key Replace local/github-actions-deploy and re-push secrets"
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help) usage 0 ;;
    --secrets-only) do_sudoers=0 ;;
    --sudoers-only) do_secrets=0 ;;
    --regenerate-key) REGENERATE=1 ;;
    *)
      echo "Unknown option: $1" >&2
      usage 1
      ;;
  esac
  shift
done

if [[ -z "${REMOTE_HOST}" ]]; then
  echo "Set REMOTE_HOST, e.g.:"
  echo "  REMOTE_HOST=209.97.142.138 $0"
  exit 1
fi

REMOTE="${REMOTE_USER}@${REMOTE_HOST}"
SCP_OPTS=(-P "${REMOTE_PORT}")

require_gh() {
  if ! command -v gh >/dev/null; then
    echo "gh CLI required for repo secrets." >&2
    exit 1
  fi
  if ! gh auth status >/dev/null 2>&1; then
    echo "gh not authenticated (run: gh auth login)." >&2
    exit 1
  fi
}

ensure_actions_key() {
  if [[ -n "${REGENERATE:-}" ]] && [[ -f "$KEY_PATH" ]]; then
    rm -f "$KEY_PATH" "${KEY_PATH}.pub"
  fi
  if [[ ! -f "$KEY_PATH" ]]; then
    echo "Generating ${KEY_PATH} (ed25519, no passphrase) ..."
    ssh-keygen -t ed25519 -N "" -f "$KEY_PATH" -C "${KEY_COMMENT}"
    chmod 600 "$KEY_PATH"
  else
    echo "Using existing key at ${KEY_PATH}"
  fi
}

install_authorized_key() {
  local fp
  fp="$(ssh-keygen -lf "${KEY_PATH}.pub" | awk '{print $2}')"
  echo "Installing public key on ${REMOTE} (fingerprint ${fp}) ..."

  scp -P "${REMOTE_PORT}" -o BatchMode=yes "${KEY_PATH}.pub" \
    "${REMOTE}:/tmp/ekcx-github-actions.pub"

  ssh -p "${REMOTE_PORT}" -o BatchMode=yes "${REMOTE}" bash -s <<'REMOTE'
set -euo pipefail
umask 077
mkdir -p ~/.ssh
touch ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
pub_file=/tmp/ekcx-github-actions.pub
pub="$(tr -d '\r' <"$pub_file")"
rm -f "$pub_file"
if grep -qxF "$pub" ~/.ssh/authorized_keys 2>/dev/null; then
  echo "authorized_keys already has this key; skipping."
else
  printf '%s\n' "$pub" >>~/.ssh/authorized_keys
  echo "Appended to authorized_keys."
fi
REMOTE
}

set_github_secrets() {
  require_gh
  echo "Setting repository Actions secrets ..."
  gh secret set DEPLOY_HOST --body "${REMOTE_HOST}"
  gh secret set DEPLOY_USER --body "${REMOTE_USER}"
  gh secret set DEPLOY_SSH_PRIVATE_KEY <"${KEY_PATH}"
  echo "Secrets set: DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_PRIVATE_KEY"
}

install_sudoers() {
  if [[ ! -f "${SUDOERS_SRC}" ]]; then
    echo "Missing ${SUDOERS_SRC}" >&2
    exit 1
  fi
  echo "Installing sudoers fragment on ${REMOTE} (one sudo password prompt) ..."
  scp "${SCP_OPTS[@]}" "${SUDOERS_SRC}" "${REMOTE}:/tmp/ekcx-deploy.sudoers"
  ssh -p "${REMOTE_PORT}" -tt "${REMOTE}" bash -s <<'REMOTE'
set -euo pipefail
sudo install -o root -g root -m 0440 /tmp/ekcx-deploy.sudoers /etc/sudoers.d/ekcx-deploy
rm -f /tmp/ekcx-deploy.sudoers
sudo visudo -cf /etc/sudoers.d/ekcx-deploy
echo "sudoers OK: jdog may restart ekcx.service and dev-ekcx.service without a password."
REMOTE
}

verify_ssh_batch() {
  echo "Verifying Actions key can SSH (BatchMode) ..."
  ssh -p "${REMOTE_PORT}" -i "${KEY_PATH}" -o BatchMode=yes -o IdentitiesOnly=yes \
    "${REMOTE}" 'echo "SSH OK for github-actions deploy key."'
}

if [[ "$do_secrets" -eq 1 ]]; then
  ensure_actions_key
  install_authorized_key
  set_github_secrets
  verify_ssh_batch
fi

if [[ "$do_sudoers" -eq 1 ]]; then
  install_sudoers
fi

if [[ "$do_sudoers" -eq 1 ]] && [[ "$do_secrets" -eq 1 ]]; then
  echo
  echo "Done. Still need on-VPS git deploy key for git pull (docs/deploy.md). Then push to staging."
fi