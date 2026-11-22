#!/usr/bin/env bash
# Create repo-root `.env` from `.env_sample` or migrate `local/shell.env` (not committed).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SAMPLE="${ROOT}/.env_sample"
TARGET="${ROOT}/.env"
LEGACY="${ROOT}/local/shell.env"

if [[ ! -f "$SAMPLE" ]]; then
  echo "Missing ${SAMPLE}" >&2
  exit 1
fi

migrate_shell_env() {
  : >"$TARGET"
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    line="${line#export }"
    line="${line#"${line%%[![:space:]]*}"}"
    key="${line%%=*}"
    val="${line#*=}"
    val="${val#\'}"; val="${val%\'}"
    val="${val#\"}"; val="${val%\"}"
    if [[ -n "$key" ]]; then
      printf '%s=%s\n' "$key" "$val" >>"$TARGET"
    fi
  done <"$LEGACY"
}

if [[ ! -f "$TARGET" ]]; then
  if [[ -f "$LEGACY" ]]; then
    echo "Migrating ${LEGACY} → ${TARGET}"
    migrate_shell_env
    echo "Done. You can remove local/shell.env."
  else
    cp "$SAMPLE" "$TARGET"
    echo "Created ${TARGET} — fill in secrets."
  fi
elif [[ -f "$LEGACY" ]]; then
  echo "Migrating ${LEGACY} → ${TARGET}"
  migrate_shell_env
  echo "Done. You can remove local/shell.env."
else
  echo "${TARGET} already exists; not overwriting."
fi

if grep -q '^EKCX_SESSION_SECRET=0000000000000000000000000000000000000000000000000000000000000000' "$TARGET" 2>/dev/null; then
  secret="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  if sed --version >/dev/null 2>&1; then
    sed -i "s/^EKCX_SESSION_SECRET=.*/EKCX_SESSION_SECRET=${secret}/" "$TARGET"
  else
    sed -i '' "s/^EKCX_SESSION_SECRET=.*/EKCX_SESSION_SECRET=${secret}/" "$TARGET"
  fi
  echo "Set EKCX_SESSION_SECRET in .env"
fi