#!/bin/bash
# Bring up the semantic routing rig and score it.
#
#   ./run-semantic.sh [bge|hash|auto] [names|tokens|real]
#
# Self-locating: everything is created under ./.work next to this script, or
# under $BENCH_HOME if you set it. Run it from anywhere.
#
# Prerequisites (checked below, with guidance if missing):
#   - python3
#   - a `thv` binary (ToolHive) on PATH or at $THV
#   - a Python interpreter with fastembed, at $EMBED_PYTHON, for the `bge` backend
#
# Linux/macOS, or WSL on Windows. Git Bash is not supported: the rig starts ~16
# local servers and depends on POSIX process handling.
set -u

BACKEND="${1:-auto}"
FIXMODE="${2:-tokens}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${BENCH_HOME:-$HERE/.work}"
EMB_PORT="${EMB_PORT:-18200}"
VMCP_PORT="${VMCP_PORT:-18091}"
BASE_PORT="${BASE_PORT:-19100}"
mkdir -p "$WORK"

die() { echo "ERROR: $*" >&2; exit 1; }

# ---------------------------------------------------------------- preflight
command -v python3 >/dev/null || die "python3 not found."

THV="${THV:-$(command -v thv || true)}"
[ -n "$THV" ] && [ -x "$THV" ] || die "ToolHive binary not found.
  Build it:  git clone --depth 1 https://github.com/stacklok/toolhive
             cd toolhive && go build -o thv ./cmd/thv
  Then:      THV=/path/to/thv $0 $BACKEND $FIXMODE"

EMBED_PYTHON="${EMBED_PYTHON:-python3}"
if [ "$BACKEND" != "hash" ]; then
  if ! "$EMBED_PYTHON" -c "import fastembed" 2>/dev/null; then
    if [ "$BACKEND" = "bge" ]; then
      die "fastembed not importable from '$EMBED_PYTHON'.
  Install:  python3 -m venv .venv && .venv/bin/pip install fastembed
  Then:     EMBED_PYTHON=\$PWD/.venv/bin/python $0 bge $FIXMODE"
    fi
    echo "note: fastembed unavailable from '$EMBED_PYTHON'; auto will fall back to hash" >&2
  fi
fi

case "$FIXMODE" in names|tokens|real) ;; *) die "fixture mode must be names, tokens or real" ;; esac

# ---------------------------------------------------------------- teardown
cleanup() {
  [ -f "$WORK/pids" ] || return 0
  while read -r pid; do kill "$pid" 2>/dev/null; done < "$WORK/pids"
  rm -f "$WORK/pids"
}
trap cleanup EXIT
cleanup
: > "$WORK/pids"

# ---------------------------------------------------------------- port map
cd "$HERE" || die "cannot enter $HERE"
python3 - "$WORK" "$BASE_PORT" <<'PY' || die "could not build the port map"
import json, sys
from real_catalogue import CATALOGUE
work, base = sys.argv[1], int(sys.argv[2])
m = {s: base + i for i, s in enumerate(CATALOGUE)}
json.dump(m, open(f"{work}/portmap.json", "w"), indent=1)
print(f"catalogue: {sum(len(v) for v in CATALOGUE.values())} tools across {len(m)} servers")
PY

# ---------------------------------------------------------------- fixtures
python3 - "$WORK" "$FIXMODE" <<'PY'
import json, subprocess, sys
work, mode = sys.argv[1], sys.argv[2]
m = json.load(open(f"{work}/portmap.json"))
with open(f"{work}/pids", "a") as pids:
    for s, p in m.items():
        proc = subprocess.Popen(["python3", "realsrv.py", s, str(p), mode],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pids.write(f"{proc.pid}\n")
print(f"fixtures: {len(m)} ({mode})")
PY
sleep 5

# ---------------------------------------------------------------- embeddings
nohup "$EMBED_PYTHON" "$HERE/embedserver.py" "$EMB_PORT" "$BACKEND" > "$WORK/embed.log" 2>&1 &
echo $! >> "$WORK/pids"
for _ in $(seq 1 90); do
  curl -sf -m 3 "http://127.0.0.1:$EMB_PORT/health" >/dev/null 2>&1 && break
  sleep 2
done
ACTUAL=$(curl -s -m 5 "http://127.0.0.1:$EMB_PORT/health" |
         python3 -c 'import sys,json;print(json.load(sys.stdin)["backend"])' 2>/dev/null)
[ -n "${ACTUAL:-}" ] || { tail -5 "$WORK/embed.log" >&2; die "embedding server did not start"; }
echo "embedding backend: $ACTUAL"
if [ "$BACKEND" = "auto" ] && [ "$ACTUAL" = "hash" ]; then
  echo "  (control backend - NOT semantic. See the README on allowlisting huggingface.co.)"
fi

# ---------------------------------------------------------------- vMCP config
python3 - "$WORK" "$EMB_PORT" <<'PY'
import json, sys
work, emb = sys.argv[1], sys.argv[2]
m = json.load(open(f"{work}/portmap.json"))
y = ["name: real-vmcp-semantic", "groupRef: real", "backends:"]
for s, p in m.items():
    y += [f"  - name: {s}", f"    url: http://127.0.0.1:{p}/mcp", "    transport: streamable-http"]
y += ["incomingAuth:", "  type: anonymous",
      "outgoingAuth:", "  source: inline", "  default:", "    type: unauthenticated",
      "aggregation:", "  conflictResolution: prefix",
      "  conflictResolutionConfig:", '    prefixFormat: "{workload}_"',
      "optimizer:", "  maxToolsToReturn: 5",
      "  embeddingProvider: openai",
      f"  embeddingService: http://127.0.0.1:{emb}/v1",
      "  embeddingModel: local-embed",
      '  hybridSearchSemanticRatio: "0.6"']
open(f"{work}/vmcp-semantic.yaml", "w").write("\n".join(y) + "\n")
PY

"$THV" vmcp validate -c "$WORK/vmcp-semantic.yaml" >/dev/null 2>&1 || die "vMCP config rejected"

nohup "$THV" vmcp serve -c "$WORK/vmcp-semantic.yaml" \
      --host 127.0.0.1 --port "$VMCP_PORT" > "$WORK/vmcp.log" 2>&1 &
echo $! >> "$WORK/pids"
for _ in $(seq 1 45); do
  curl -sf -m 3 "http://127.0.0.1:$VMCP_PORT/health" >/dev/null 2>&1 && break
  sleep 2
done

# ---------------------------------------------------------------- score
BEFORE=$(curl -s -m 5 "http://127.0.0.1:$EMB_PORT/health" |
         python3 -c 'import sys,json;print(json.load(sys.stdin)["requests"])' 2>/dev/null || echo 0)

python3 realbench.py "ToolHive-hybrid-${ACTUAL}" \
        "http://127.0.0.1:$VMCP_PORT/mcp" find_tool tool_description text 2>&1 | tail -2

AFTER=$(curl -s -m 5 "http://127.0.0.1:$EMB_PORT/health" |
        python3 -c 'import sys,json;print(json.load(sys.stdin)["requests"])' 2>/dev/null || echo 0)
echo "embedding requests during run: $((AFTER - BEFORE)) (0 would mean the semantic arm never ran)"
