#!/usr/bin/env bash
# Write Resend + mail vars to repo-root `.env` and ensure ~/.zshrc sources it.
#
#   ./local/setup-shell-env.sh              # prompts for API key
#   ./local/setup-shell-env.sh re_xxxx      # key on command line (shell history — prefer prompt)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=shell-env-common.sh
source "${SCRIPT_DIR}/shell-env-common.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") [RESEND_API_KEY]

Writes ${ENV_FILE} (gitignored) and adds a source block to ${ZSHRC}.

Then: source ~/.zshrc   (or open a new terminal)
EOF
}

read_api_key() {
  local key=""
  if [[ ! -t 0 ]]; then
    echo "No TTY; pass the key as an argument." >&2
    exit 1
  fi
  read -r -s -p "Resend API key (re_...): " key
  echo >&2
  if [[ -z "$key" ]]; then
    echo "No API key provided." >&2
    exit 1
  fi
  printf '%s' "$key"
}

main() {
  local api_key="${1-}"
  if [[ "${api_key:-}" == "-h" || "${api_key:-}" == "--help" ]]; then
    usage
    exit 0
  fi
  if [[ -z "$api_key" ]]; then
    api_key="$(read_api_key)"
  fi
  api_key="${api_key#"${api_key%%[![:space:]]*}"}"
  api_key="${api_key%"${api_key##*[![:space:]]}"}"
  if [[ ! "$api_key" =~ ^re_ ]]; then
    echo "Warning: key does not start with re_ (continuing anyway)." >&2
  fi

  set_shell_env_var RESEND_API_KEY "$api_key"
  set_shell_env_var EKCX_EMAIL_MODE resend
  set_shell_env_var EKCX_EMAIL_FROM 'EKCX <noreply@mail.ekcx.co.uk>'
  echo "Wrote ${ENV_FILE}"

  install_zshrc_block

  echo
  echo "Run:  source ~/.zshrc"
  echo "Test mail: ./local/send-test-email.sh jbknight07@gmail.com"
  echo "Session:   ./local/generate-session-secret.sh && source ~/.zshrc"
}

main "$@"