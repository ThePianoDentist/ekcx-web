# Shared helpers for local/shell.env + ~/.zshrc (source from other local/*.sh scripts).
ROOT="$(cd "$(dirname "${BASH_SOURCE[1]:-$0}")" && pwd)"
ENV_FILE="${ROOT}/shell.env"
ZSHRC="${HOME}/.zshrc"
MARKER_START="# >>> ekcx-web local env >>>"
MARKER_END="# <<< ekcx-web local env <<<"

install_zshrc_block() {
  python3 - "$ZSHRC" "$ENV_FILE" "$MARKER_START" "$MARKER_END" <<'PY'
import pathlib
import re
import sys

zshrc = pathlib.Path(sys.argv[1])
env_file = pathlib.Path(sys.argv[2])
start, end = sys.argv[3], sys.argv[4]
block = f"{start}\n[[ -f {env_file} ]] && source {env_file}\n{end}"
text = zshrc.read_text() if zshrc.exists() else ""
pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
if pattern.search(text):
    text = pattern.sub(block, text)
    action = "Updated"
else:
    text = text.rstrip("\n") + "\n\n" + block + "\n"
    action = "Appended to"
zshrc.write_text(text)
print(f"{action} {zshrc} (ekcx-web block).")
PY
}

quote_single() {
  local v="$1"
  v="${v//\'/\'\\\'\'}"
  printf "'%s'" "$v"
}

# Set or replace export KEY='value' in shell.env (preserves other lines).
set_shell_env_var() {
  local key="$1"
  local value="$2"
  local header="${3-# ekcx-web local env — do not commit.}"

  umask 077
  python3 - "$ENV_FILE" "$key" "$value" "$header" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
header = sys.argv[4]
line = f"export {key}={value!r}"

lines: list[str] = []
if path.exists():
    lines = path.read_text().splitlines()
else:
    lines = [header]

lines = [ln for ln in lines if not ln.startswith(f"export {key}=")]
if not lines or not lines[0].startswith("#"):
    lines.insert(0, header)
lines.append(line)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text("\n".join(lines) + "\n")
PY
  chmod 600 "$ENV_FILE"
}