#!/usr/bin/env bash
# Install systemd EnvironmentFile for ekcx / dev-ekcx and set secrets on the VPS.
#
#   git pull
#   sudo ./scripts/server-ekcx-env.sh install
#   sudo ./scripts/server-ekcx-env.sh set RESEND_API_KEY
#   sudo ./scripts/server-ekcx-env.sh set EKCX_SESSION_SECRET "$(openssl rand -hex 32)"
#
# Values live in /etc/ekcx/environment (not in git). Requires root.
set -euo pipefail

ENV_FILE="/etc/ekcx/environment"
UNITS=(ekcx.service dev-ekcx.service)

usage() {
  cat <<'EOF'
Usage:
  server-ekcx-env.sh install
      Create /etc/ekcx/environment and systemd drop-ins (idempotent).

  server-ekcx-env.sh set NAME [VALUE]
      Set NAME in the environment file (prompts securely if VALUE omitted).

  server-ekcx-env.sh unset NAME
      Remove NAME from the environment file.

  server-ekcx-env.sh show
      List variable names (values masked).

  server-ekcx-env.sh apply
      systemctl daemon-reload and restart ekcx + dev-ekcx if units exist.

After set/unset, services are restarted automatically unless EKCX_ENV_NO_RESTART=1.
EOF
}

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Run with sudo." >&2
    exit 1
  fi
}

valid_name() {
  local name="$1"
  if [[ ! "$name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "Invalid env name: $name" >&2
    exit 1
  fi
}

systemd_quote() {
  local v="$1"
  if [[ "$v" =~ ^[A-Za-z0-9_./:+@-]+$ ]]; then
    printf '%s' "$v"
    return
  fi
  local escaped="${v//\\/\\\\}"
  escaped="${escaped//\"/\\\"}"
  printf '"%s"' "$escaped"
}

install_layout() {
  install -d -m 0755 -o root -g root /etc/ekcx
  if [[ ! -f "$ENV_FILE" ]]; then
    install -o root -g jdog -m 0640 /dev/null "$ENV_FILE"
  else
    chown root:jdog "$ENV_FILE"
    chmod 0640 "$ENV_FILE"
  fi

  for unit in "${UNITS[@]}"; do
    local dropin="/etc/systemd/system/${unit}.d"
    install -d -m 0755 -o root -g root "$dropin"
    cat >"${dropin}/environment.conf" <<EOF
[Service]
EnvironmentFile=-${ENV_FILE}
EOF
    chmod 0644 "${dropin}/environment.conf"
    echo "drop-in: ${dropin}/environment.conf"
  done
}

read_env_lines() {
  [[ -f "$ENV_FILE" ]] || return 0
  grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$' || true
}

write_env_file() {
  local tmp
  tmp="$(mktemp)"
  chmod 0640 "$tmp"
  chown root:jdog "$tmp"
  printf '%s\n' "$@" >"$tmp"
  mv -f "$tmp" "$ENV_FILE"
  chown root:jdog "$ENV_FILE"
  chmod 0640 "$ENV_FILE"
}

cmd_set() {
  local name="$1"
  local value="${2-}"
  valid_name "$name"
  if [[ -z "$value" ]]; then
    if [[ ! -t 0 ]]; then
      echo "Provide VALUE on the command line when stdin is not a TTY." >&2
      exit 1
    fi
    read -r -s -p "Value for ${name}: " value
    echo >&2
    if [[ -z "$value" ]]; then
      echo "Empty value; not set." >&2
      exit 1
    fi
  fi

  local -a lines=()
  local line key
  while IFS= read -r line; do
    key="${line%%=*}"
    if [[ "$key" == "$name" ]]; then
      continue
    fi
    lines+=("$line")
  done < <(read_env_lines)

  lines+=("${name}=$(systemd_quote "$value")")
  write_env_file "${lines[@]}"
  echo "Set ${name}"
}

cmd_unset() {
  local name="$1"
  valid_name "$name"
  local -a lines=()
  local line key found=0
  while IFS= read -r line; do
    key="${line%%=*}"
    if [[ "$key" == "$name" ]]; then
      found=1
      continue
    fi
    lines+=("$line")
  done < <(read_env_lines)
  if [[ "$found" -eq 0 ]]; then
    echo "No such variable: ${name}" >&2
    exit 1
  fi
  write_env_file "${lines[@]}"
  echo "Unset ${name}"
}

mask_value() {
  local v="$1"
  local len="${#v}"
  if [[ "$len" -le 4 ]]; then
    printf '****'
    return
  fi
  printf '%s****%s' "${v:0:2}" "${v: -2}"
}

cmd_show() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "(no ${ENV_FILE} — run: sudo $0 install)"
    return
  fi
  local line key val
  while IFS= read -r line; do
    key="${line%%=*}"
    val="${line#*=}"
    val="${val#\"}"
    val="${val%\"}"
    if [[ "$key" =~ (^|_)(KEY|SECRET|PASSWORD|TOKEN)(_|$) ]] || [[ "$key" == *KEY* ]] || [[ "$key" == *SECRET* ]]; then
      printf '%s=%s\n' "$key" "$(mask_value "$val")"
    else
      printf '%s=%s\n' "$key" "$val"
    fi
  done < <(read_env_lines)
}

cmd_apply() {
  systemctl daemon-reload
  for unit in "${UNITS[@]}"; do
    if systemctl cat "$unit" &>/dev/null; then
      systemctl restart "$unit"
      echo "restarted ${unit}"
    fi
  done
}

main() {
  if [[ $# -lt 1 ]]; then
    usage >&2
    exit 1
  fi
  require_root
  local cmd="$1"
  shift

  case "$cmd" in
    install)
      install_layout
      systemctl daemon-reload
      echo "Installed. Add secrets with: sudo $0 set RESEND_API_KEY"
      ;;
    set)
      [[ $# -ge 1 ]] || {
        echo "set requires NAME" >&2
        exit 1
      }
      install_layout
      cmd_set "$@"
      if [[ "${EKCX_ENV_NO_RESTART:-}" != 1 ]]; then
        cmd_apply
      fi
      ;;
    unset)
      [[ $# -eq 1 ]] || {
        echo "unset requires NAME" >&2
        exit 1
      }
      cmd_unset "$1"
      if [[ "${EKCX_ENV_NO_RESTART:-}" != 1 ]]; then
        cmd_apply
      fi
      ;;
    show)
      cmd_show
      ;;
    apply)
      cmd_apply
      ;;
    -h | --help | help)
      usage
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"