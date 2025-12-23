#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$ROOT_DIR/venv-trading-bot/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/venv-trading-bot/bin/activate"
fi

python "$ROOT_DIR/dashboard.py" &
DASHBOARD_PID=$!

python "$ROOT_DIR/trading_bot.py" &
BOT_PID=$!

trap 'kill "$BOT_PID" "$DASHBOARD_PID"' SIGINT SIGTERM
wait "$BOT_PID" "$DASHBOARD_PID"
