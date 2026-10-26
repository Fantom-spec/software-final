#!/bin/bash
# Real-browser verification + screenshots against the demo server (needs Node.js 18+ and network access for npm).
#   scripts/run_browser_checks.sh [port]
# Writes assessment9_ui/docs/browser_verification.txt and assessment9_ui/screenshots/*.png (+ manifest.json).
set -e
cd "$(dirname "$0")/.."
PORT="${1:-5055}"
( cd scripts/browser && [ -d node_modules ] || npm install --no-audit --no-fund )
if curl -s -o /dev/null "http://127.0.0.1:$PORT/auth/login"; then echo "Port $PORT is already in use; stop that server first." >&2; exit 1; fi
python scripts/serve_demo.py "$PORT" > /tmp/hms_demo_server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$PORT/auth/login" && break; sleep 0.5; done
mkdir -p assessment9_ui/docs assessment9_ui/screenshots
{
  echo "# Browser verification: scripts/browser/verify_ui.mjs against scripts/serve_demo.py"
  echo "# Run: $(date -Iseconds)   Browser: headless Chromium via puppeteer-core"
  node scripts/browser/verify_ui.mjs "http://127.0.0.1:$PORT" || true
} > assessment9_ui/docs/browser_verification.txt
cat assessment9_ui/docs/browser_verification.txt | tail -5
# Fresh server on another port so the screenshots start from a known data state (the checks above changed data)
kill $SERVER 2>/dev/null; wait $SERVER 2>/dev/null || true
PORT2=$((PORT + 1))
if curl -s -o /dev/null "http://127.0.0.1:$PORT2/auth/login"; then echo "Port $PORT2 is already in use." >&2; exit 1; fi
python scripts/serve_demo.py "$PORT2" > /tmp/hms_demo_server2.log 2>&1 &
SERVER=$!
for i in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$PORT2/auth/login" && break; sleep 0.5; done
rm -f assessment9_ui/screenshots/*.png
node scripts/browser/capture_screenshots.mjs "http://127.0.0.1:$PORT2" "$PWD/assessment9_ui/screenshots"
