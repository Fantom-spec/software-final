#!/bin/bash
# Refresh the reference screenshots and rebuild assessment8_testing/manual_testing/Manual_Test_Document.docx/.pdf
#   scripts/run_manual_doc.sh [port]
# Needs: Python venv with requirements-test.txt, Node.js 18+, network for `npm install` (headless Chromium + docx).
# Reference screenshots show the EXPECTED screens (captured by script). They are not evidence of manual execution.
set -e
cd "$(dirname "$0")/.."
PORT="${1:-5066}"
( cd scripts/browser && [ -d node_modules ] || npm install --no-audit --no-fund )
if curl -s -o /dev/null "http://127.0.0.1:$PORT/auth/login"; then echo "Port $PORT is already in use." >&2; exit 1; fi
LOGIN_MAX_ATTEMPTS=5 DEMO_ALLOCATIONS=0 python scripts/serve_demo.py "$PORT" > /tmp/hms_manual_doc_server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for i in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$PORT/auth/login" && break; sleep 0.5; done
node scripts/browser/capture_manual_case_screens.mjs "http://127.0.0.1:$PORT" "$PWD/assessment8_testing/manual_testing/reference_screenshots"
kill $SERVER 2>/dev/null; wait $SERVER 2>/dev/null || true
python scripts/build_manual_test_document.py
