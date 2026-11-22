#!/usr/bin/env bash
# Generate EKCX_SESSION_SECRET for local dev (admin sessions) and store in local/shell.env.
#
#   ./local/generate-session-secret.sh
#   source ~/.zshrc
#   make run
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=shell-env-common.sh
source "${SCRIPT_DIR}/shell-env-common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0")

Generates EKCX_SESSION_SECRET (64 hex chars) into ${ENV_FILE}
and ensures ~/.zshrc sources that file.

Then: source ~/.zshrc
EOF
}

main() {
  if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
  fi
  if [[ $# -gt 0 ]]; then
    echo "No arguments expected." >&2
    usage >&2
    exit 1
  fi

  local secret
  secret="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  set_shell_env_var EKCX_SESSION_SECRET "$secret"

  echo "Wrote EKCX_SESSION_SECRET to ${ENV_FILE}"
  install_zshrc_block
  echo
  echo "Run:  source ~/.zshrc"
  echo "Then: make run"
}

main "$@"