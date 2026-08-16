#!/bin/bash
# Bring up the full semantic rig and score it.
#   run-semantic.sh <bge|hash|auto> [fixture-mode]
# Once huggingface.co is allowlisted, `run-semantic.sh bge` is the whole run.
set -u
BACKEND="${1:-auto}"
FIXMODE="${2:-tokens}"
S=/tmp/claude-0/-home-user-skills/b2314177-3001-5000-9dbc-89ac5523896e/scratchpad
EMB_PORT=18200
VMCP_PORT=18091

for pat in embedserver "thv vmcp" realsrv; do pkill -f "$pat" >/dev/null 2>&1; done
sleep 3

# 1. fixtures
cd "$S/fixture" || exit 1
python3 - "$FIXMODE" <<'PY'
import json, subprocess, sys
mode = sys.argv[1]
m = json.load(open('/tmp/claude-0/-home-user-skills/b2314177-3001-5000-9dbc-89ac5523896e/scratchpad/portmap.json'))
for s, p in m.items():
    subprocess.Popen(['python3', 'realsrv.py', s, str(p), mode],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f'fixtures: {len(m)} ({mode})')
PY
sleep 5

# 2. local embedding endpoint
nohup "$S/embvenv/bin/python" "$S/fixture/embedserver.py" "$EMB_PORT" "$BACKEND" > "$S/embed.log" 2>&1 &
for _ in $(seq 1 60); do
  curl -sf -m 3 "http://127.0.0.1:$EMB_PORT/health" >/dev/null 2>&1 && break
  sleep 2
done
ACTUAL=$(curl -s -m 5 "http://127.0.0.1:$EMB_PORT/health" | python3 -c 'import sys,json;print(json.load(sys.stdin)["backend"])' 2>/dev/null)
echo "embedding backend: ${ACTUAL:-UNAVAILABLE}"
[ -z "${ACTUAL:-}" ] && { echo "FATAL: embedding server did not start"; tail -5 "$S/embed.log"; exit 1; }

# 3. vMCP with the semantic arm on
cd "$S" || exit 1
nohup "$S/bin/thv" vmcp serve -c "$S/vmcp-semantic.yaml" --host 127.0.0.1 --port "$VMCP_PORT" > "$S/vmcp-sem.log" 2>&1 &
sleep 30

BEFORE=$(curl -s -m 5 "http://127.0.0.1:$EMB_PORT/health" | python3 -c 'import sys,json;print(json.load(sys.stdin)["requests"])' 2>/dev/null)

# 4. score
cd "$S/fixture" || exit 1
python3 realbench.py "ToolHive-hybrid-${ACTUAL}" "http://127.0.0.1:$VMCP_PORT/mcp" find_tool tool_description text 2>&1 | tail -2

AFTER=$(curl -s -m 5 "http://127.0.0.1:$EMB_PORT/health" | python3 -c 'import sys,json;print(json.load(sys.stdin)["requests"])' 2>/dev/null)
echo "embedding requests during run: $((AFTER - BEFORE)) (proves the semantic arm was exercised)"
