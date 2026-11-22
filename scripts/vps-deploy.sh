#!/usr/bin/env bash
# Run on the VPS from the repo root after git pull (also invoked by GitHub Actions).
set -euo pipefail

UV="${UV:-/home/jdog/.local/bin/uv}"

usage() {
  echo "Usage: $0 staging|production" >&2
  exit 1
}

[[ $# -eq 1 ]] || usage

case "$1" in
  staging)
    expected_root="/home/jdog/ekcx-dev"
    expected_branch="staging"
    unit="dev-ekcx.service"
    ;;
  production)
    expected_root="/home/jdog/ekcx-web"
    expected_branch="main"
    unit="ekcx.service"
    ;;
  *)
    usage
    ;;
esac

root="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "$root" != "$expected_root" ]]; then
  echo "Expected repo at $expected_root, got $root" >&2
  exit 1
fi

branch="$(git -C "$root" rev-parse --abbrev-ref HEAD)"
if [[ "$branch" != "$expected_branch" ]]; then
  echo "Expected branch $expected_branch, on $branch" >&2
  exit 1
fi

if [[ ! -x "$UV" ]]; then
  echo "uv not found at $UV" >&2
  exit 1
fi

cd "$root"
"$UV" sync
"$UV" run alembic upgrade head
sudo systemctl restart "$unit"