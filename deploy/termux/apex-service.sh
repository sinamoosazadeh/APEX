#!/data/data/com.termux/files/usr/bin/bash
# APEX supervised service loop (Book II 29.20: watchdog + auto recovery).
# The OS wrapper IS the supervisor: apex is restart-safe by design
# (durable stores, event archive, checkpointed state - 13.20), so on
# any exit the loop backs off and relaunches. Ctrl+C twice to stop.
set -u
cd "$(dirname "$0")/../.."

termux-wake-lock 2>/dev/null || true
BACKOFF=5
while true; do
  echo "[apex-service] starting operational loop ($(date -u +%FT%TZ))"
  uv run apex schedule --run || true
  uv run apex run --seconds 0
  CODE=$?
  echo "[apex-service] loop exited code=$CODE; restarting in ${BACKOFF}s"
  sleep "$BACKOFF"
  if [ "$BACKOFF" -lt 300 ]; then BACKOFF=$((BACKOFF * 2)); fi
done
