#!/usr/bin/env bash
# Send a Resend smoke-test email (sources local/shell.env).
#
#   ./local/send-test-email.sh
#   ./local/send-test-email.sh jbknight07@gmail.com
#
# Until mail.ekcx.co.uk is verified in Resend, uses onboarding@resend.dev as From.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=shell-env-common.sh
source "${SCRIPT_DIR}/shell-env-common.sh"

ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TO="${1:-${EKCX_TEST_EMAIL:-jbknight07@gmail.com}}"
SANDBOX_FROM="${EKCX_SANDBOX_FROM:-onboarding@resend.dev}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ${ENV_FILE}. Run ./local/setup-shell-env.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ -z "${RESEND_API_KEY:-}" ]]; then
  echo "RESEND_API_KEY not set in ${ENV_FILE}." >&2
  exit 1
fi

export EKCX_EMAIL_MODE="${EKCX_EMAIL_MODE:-resend}"

if [[ -z "${EKCX_EMAIL_FROM:-}" ]]; then
  export EKCX_EMAIL_FROM="$SANDBOX_FROM"
  echo "EKCX_EMAIL_FROM unset; using sandbox From: ${SANDBOX_FROM}" >&2
elif [[ "$EKCX_EMAIL_FROM" == *mail.ekcx.co.uk* ]]; then
  export EKCX_EMAIL_FROM="$SANDBOX_FROM"
  echo "Domain may be unverified; using sandbox From: ${SANDBOX_FROM}" >&2
fi

cd "$ROOT"
exec uv run python -m app.mail.interfaces.scripts.send_test_email --to "$TO"