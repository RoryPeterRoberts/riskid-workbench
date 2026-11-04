#!/usr/bin/env bash
# PLAN.md round 14: `pipx install .` and `riskid serve` work in a clean virtualenv.
# Installs the workbench from this repository into a throwaway pipx home, creates an
# organisation file, serves it, and checks that the Inventory screen and a PDF answer.
# Needs network access for the dependencies; run it by hand, or with
# RISKID_SHELL_TESTS=1 python -m pytest tests/test_install.py.
set -euo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
work="$(mktemp -d)"
trap 'kill "${server:-0}" 2>/dev/null || true; rm -rf "$work"' EXIT
export PIPX_HOME="$work/pipx" PIPX_BIN_DIR="$work/bin"
if ! pipx install "$repo" >"$work/install.log" 2>&1; then
  tail -20 "$work/install.log"
  exit 1
fi
"$work/bin/riskid" init "$work/org.riskid"
port=$(python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')
"$work/bin/riskid" serve "$work/org.riskid" --port "$port" --no-browser &
server=$!
code=000
for _ in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/inventory" || true)
  [ "$code" = "200" ] && break
  sleep 1
done
[ "$code" = "200" ] || { echo "riskid serve did not answer (last status $code)"; exit 1; }
pdf=$(curl -s "http://127.0.0.1:$port/documents/report.pdf" | head -c 5)
[ "$pdf" = "%PDF-" ] || { echo "the board report did not come back as a PDF"; exit 1; }
echo "ok: pipx installed $("$work/pipx/venvs/riskid-workbench/bin/python" --version 2>&1), riskid serve answered on $port"
