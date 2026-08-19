# MCP routing benchmark harness

Scores an MCP gateway on whether it returns the right tool for a
natural-language request. Used to produce
[`../mcp-tool-routing-layer-validation.md`](../mcp-tool-routing-layer-validation.md).

No dependencies beyond the Python standard library.

## Files

| File | Purpose |
|---|---|
| `mcpsrv.py` | Fixture MCP server over **stdio**. 4 catalogues × 4 tools. |
| `mcphttp.py` | Same catalogues over **streamable HTTP** (gateways that only take URLs). |
| `mcpclient.py` | Minimal streamable-HTTP MCP client. Run directly to list a gateway's tool surface. |
| `bench.py` | Scores top-1/top-3/top-5 and latency over 16 paraphrased queries. |

## Use

Start the fixtures:

```bash
python3 mcphttp.py payments 19001 &
python3 mcphttp.py infra 19002 &
python3 mcphttp.py crm 19003 &
python3 mcphttp.py observability 19004 &
```

Point your gateway at those four URLs, then check its surface and score it:

```bash
python3 mcpclient.py http://127.0.0.1:PORT/mcp
python3 bench.py http://127.0.0.1:PORT/mcp <search-tool> <query-arg> ['{"extra":"args"}']
```

Examples that were run:

```bash
python3 bench.py http://127.0.0.1:18080/mcp retrieve_tools query      # MCPProxy
python3 bench.py http://127.0.0.1:18090/mcp find_tool tool_description # ToolHive vMCP
```

## Picking this up cold

Start with [`HANDOVER.md`](./HANDOVER.md) — background, what is settled, what is
still open, and why. To resume the work in a fresh session, paste
[`HANDOVER-PROMPT.md`](./HANDOVER-PROMPT.md) into it.

## Semantic run (one command, once embeddings are available)

```bash
bash run-semantic.sh bge          # real embeddings
bash run-semantic.sh hash         # lexical control
bash run-semantic.sh auto         # bge if the model loads, else hash
```

`run-semantic.sh` brings up the fixtures, starts `embedserver.py`, starts vMCP with
`vmcp-semantic.example.yaml`, scores the 43 queries, and prints how many embedding
requests the run actually made — so you can prove the semantic arm was exercised
rather than assume it.

| File | Purpose |
|---|---|
| `embedserver.py` | Local OpenAI-compatible `/v1/embeddings`. Nothing leaves the machine. |
| `vmcp-semantic.example.yaml` | vMCP config with `embeddingProvider: openai` and `hybridSearchSemanticRatio: "0.6"`. |
| `run-semantic.sh` | Brings the whole rig up and scores it. |

### The two backends

- **`bge`** — `fastembed` with `BAAI/bge-small-en-v1.5`, ToolHive's default model.
  Real sentence embeddings. Needs a one-time model download from `huggingface.co`.
- **`hash`** — deterministic hashed bag-of-words in 384 dims. **Not semantic** by
  construction: `cos("refund a charge", "give the money back") = 0.0`. It exists to
  prove the wiring without the model, and as a control — if hybrid-with-`hash`
  scores like plain lexical while hybrid-with-`bge` scores much better, the gain is
  attributable to semantics rather than to the hybrid plumbing.

### Status of the rig

Verified end to end with the `hash` backend: **44 embedding requests** across 43
queries, confirming ToolHive's semantic arm calls the endpoint and the OpenAI
provider path works. Scores (`top-1 21%, top-3 33%, top-5 44%, 0 empty, 48 ms`)
are the control's, not a semantic result — spending 60% of the result budget on a
non-semantic embedder costs top-3, exactly as expected. Median latency rises from
3 ms to 48 ms, which is the embedding round-trip per query.

Everything except the model weights is proven. Only ToolHive has a semantic mode;
MCPProxy is lexical-only in shipped code and Nexus is Tantivy-only, so this run
answers "does hybrid beat lexical" rather than being a three-way comparison.

### Getting the model

`huggingface.co` is blocked by the environment's network policy. To allow it, open
[claude.ai/code](https://claude.ai/code), click the cloud icon above the message
box, edit the environment, set **Network access** to **Custom**, and add:

```text
huggingface.co
*.huggingface.co
```

Tick **"Also include default list of common package managers"** — Custom replaces
the Trusted list entirely, and without it PyPI and npm stop resolving. The change
applies to sessions started afterwards; running sessions keep the config they
started with.

## Reading the results

The 16 queries deliberately avoid the tools' own vocabulary ("bounce a stuck
container" for `restart_pod`), which isolates the retrieval mechanism by removing
lexical overlap. Scores are therefore **much lower than real-world usage** and are
only meaningful *relative to each other*.

Two things to adjust before trusting a number for your own stack:

- Replace the catalogues in `mcpsrv.py` with your real tool names and descriptions.
- Add your servers to the `servers` tuple in `bench.py::names_in`, which strips
  `server_`/`server:`/`server__` prefixes. Gateways that prefix tool names will
  otherwise score 0.

## Where this is meant to run

The rig starts ~16 local servers, needs the ToolHive `thv` binary, and drives
everything over localhost. Run it on **Linux or macOS**, or under **WSL** on
Windows. Git Bash (MINGW64) is not supported.

`run-semantic.sh` is self-locating: it creates everything it needs under
`./.work` next to the script (override with `BENCH_HOME`), generates its own port
map and vMCP config from `real_catalogue.py`, and kills what it started on exit.
It does not assume any path outside its own directory.

Point it at the two things it can't build for you:

```bash
git clone --depth 1 https://github.com/stacklok/toolhive && \
  (cd toolhive && go build -o thv ./cmd/thv)
python3 -m venv .venv && .venv/bin/pip install fastembed

THV=$PWD/toolhive/thv EMBED_PYTHON=$PWD/.venv/bin/python \
  ./run-semantic.sh bge tokens
```

Both are checked up front, and a missing one prints the exact command to fix it
rather than failing partway through.

The simpler path is to let a Claude Code cloud session run it — the toolchain is
already there, and only the `huggingface.co` allowlist is missing.
