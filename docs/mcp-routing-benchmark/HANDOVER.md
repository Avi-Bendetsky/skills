# Handover: MCP tool-routing layer evaluation

**Status:** complete. The semantic measurement ran on 29 September 2026 (Run 4).
**Last worked:** 29 September 2026.

If you only read one thing: **the pre-registered verdict is "semantic materially
beats lexical" (top-3 56% vs 33% for the non-semantic control, p = 0.006), and the
recommendation stands:** Anthropic's tool search for selection, with ToolHive or
MCPProxy only for running, authenticating and isolating servers. Against pure
lexical search, embeddings double top-1 (21% → 44%), but the top-3 gain (44% → 56%)
is not significant. The full result is
[Run 4 in the validation doc](../mcp-tool-routing-layer-validation.md#run-4-semantic-2026-09-29),
run under the pre-registered [`PROTOCOL-run4.md`](./PROTOCOL-run4.md).

The `huggingface.co` blocker described in §4-§5 applied only to the Claude Code
cloud environments. Run 4 ran on a Linux container where the model could be fetched
once and then run locally. §4-§5 are kept as the record of how the blocker was
diagnosed.

---

## 1. The original question

> A tool-calling layer between MCP servers and the context window, so thousands of
> MCPs can be installed and the layer calls only the one best for the job.
> Must be battle-tested and robust.

---

## 2. What was produced

| Artefact | What it is |
|---|---|
| [`../mcp-tool-routing-layer-evaluation.md`](../mcp-tool-routing-layer-evaluation.md) | Top 10 options, assessed by cloning and reading source, not READMEs |
| [`../mcp-tool-routing-layer-validation.md`](../mcp-tool-routing-layer-validation.md) | Build + test results for every candidate, and four benchmark runs (Run 4 = semantic) |
| `./` (this directory) | The benchmark harness, the real 412-tool catalogue, the semantic rig, `PROTOCOL-run4.md`, `compare.py` and `results/run4/` |

The Runs 1-3 artefacts were merged to `main` via PRs #1, #3, #4, #5, #7, #8 and #9
(scorer audit). Run 4 is on branch `claude/go-bd9ae8`.

---

## 3. Conclusions that are settled

**Use Anthropic's tool search for selection.** It is already on by default, handles
10,000 tools, is server-side, and preserves prompt caching. Add a self-hosted layer
only for what it does *not* do: running, authenticating, isolating and governing
MCP servers.

**Scale destroys lexical routing.** Measured on the real catalogue (top-1 falls
from 69-81% on a 16-tool toy to 21-28%):

| Catalogue | ToolHive | MCPProxy | Nexus |
|---|---|---|---|
| 16-tool toy, top-1 | 81% | 69% | 69% |
| **412 real tools, top-1** | 21% | 26% | **28%** |
| **412 real tools, top-3** | **44%** | 37% | 37% |
| **412 real tools, empty** | **1/43** | 8/43 | 6/43 |

(MCPProxy and Nexus figures corrected 2026-08-24 after a scorer audit — see
"Scorer audit" in the validation doc. ToolHive unchanged.)

Any decision taken from a small demo overstates these layers by 3-4x.

**Real descriptions do not rescue it.** Measured by enriching one complete server
(Supabase, all 29 tools) with verbatim live descriptions: net effect across 43
queries was noise (post-audit top-1: ToolHive 21%→19%, MCPProxy 26%→28%, Nexus
28%→28%). Run 4 found the same for embeddings. Do not spend time exporting the real
catalogue with descriptions — it was tested and it does not change the ranking.

**The separators that actually matter at 412 tools:**

- **Empty results.** ToolHive returned nothing 1 time in 43; MCPProxy 8; Nexus 6.
  An empty result gives the model nothing to reason with.
- **Description sensitivity.** MCPProxy collapses to 2% top-1 with 34/43 empty when
  servers ship no descriptions, because its Bleve mapping uses a *keyword* analyser
  on the tool-name field. ToolHive and Nexus tokenise names and are unaffected.
- **Tool-surface overhead.** ToolHive and Nexus expose 2 tools; MCPProxy exposes 12.

**Recommendation:** ToolHive vMCP if you want a self-hosted router — best top-3
(44% vs 37%), near-zero empty rate (1/43), hybrid search, 86-100% coverage on the
routing path — at the cost of a heavy config and an optimizer its own docs mark
Experimental. MCPProxy if you want a single local binary and have good descriptions
everywhere; it leads on top-1 (26% vs 21%) but returns nothing 8 times in 43.
Nexus scores best of all on top-1 (28%) and is still not recommendable: no release
since September 2025. The best-scoring lexical engine here is the unmaintained one.
These top-1 comparisons are lexical-only. With its semantic arm on, ToolHive
measured 44% top-1 / 56% top-3 in Run 4 (a cross-run comparison, not
significance-tested). That did not meet the pre-registered bar to change the
selection recommendation above.

---

## 4. The one open question (answered in Run 4)

**Does semantic search beat the ~21% lexical ceiling?** The pre-registered verdict
is "semantic materially beats lexical": top-3 56% vs 33% for the non-semantic
control, p = 0.006. Against pure lexical search, top-1 doubles (21% → 44%,
p = 0.021, unadjusted), but the top-3 gain (44% → 56%) is not significant
(p = 0.18), and the verdict clears its 10-point bar by one query. "change the
schema safely" is still missed. The recommendation is unchanged. Details are in
Run 4 of the validation doc.

The rest of this section and §5 record the question and the blocker as they stood
before Run 4.

This matters because the failures are semantic, not lexical. The clearest example:
"change the schema safely" never matched `apply_migration` in any engine in any
condition, because that tool is described as *"Use this when executing DDL
operations"*. No amount of keyword matching bridges "schema safely" → "DDL". That is
exactly the gap embeddings exist to close. At the time it was also exactly what
could not be tested. (Run 4 tested it: bge-small still misses it.)

### Why it was blocked (historical)

`huggingface.co` returns `403` at the egress proxy — an organisation policy denial:

```
$ curl -sS "$HTTPS_PROXY/__agentproxy/status"
recentRelayFailures: [{'kind': 'connect_rejected',
  'detail': 'gateway answered 403 to CONNECT (policy denial or upstream failure)',
  'host': 'huggingface.co:443'}]
```

Confirmed blocked in **both** of the account's cloud environments
(`env_013GTHpMXmZ2cV2Uz1JPooaQ` and `env_01Rxy9pSf2YduFNNkCTBehHU`) by spawning a
fresh session in each. It is not a case of the wrong environment being edited — the
change has simply not been made.

**Do not route around this.** The proxy's own README says organisation policy
denials must be reported, not worked around. No mirrors, no alternate model hosts.

### How to clear it

At [claude.ai/code](https://claude.ai/code):

1. Click the **cloud icon showing the environment name**, in the row directly above
   the message box. There is no settings page and no direct URL for this.
2. Hover an environment row, click the **gear** icon.
3. Set **Network access** to **Custom**.
4. In **Allowed domains**:
   ```
   huggingface.co
   *.huggingface.co
   ```
   Both lines — a leading `*.` matches subdomains only, and the weights come from
   `cdn-lfs*.huggingface.co` while metadata comes from the apex.
5. **Tick "Also include default list of common package managers."** Custom *replaces*
   the Trusted list; without this, PyPI and npm stop resolving and unrelated builds
   break.
6. Save. **The change applies only to sessions started afterwards.**

While in there, rename the environments — there are currently two both called
"Default", which is indistinguishable in the picker and cost a wasted round trip.

There is no API for any of this. `list_environments` is the only environment tool;
nothing can create or modify one. It is a UI action.

### Alternatives, in preference order

1. **Allowlist `huggingface.co`** — one-time model download, then all inference is
   local. Preferred: a routing layer sees every query, and queries are user intent.
2. **Docker daemon + `ghcr.io`** — lets ToolHive run its TEI container. Closest to
   production, heaviest setup.
3. **An external embeddings API** — cheapest to arrange, but ships every query
   off-network in perpetuity. Least preferred for this component specifically.

---

## 5. Running the remaining work

Once the allowlist is saved, in a **new** session:

```bash
cd docs/mcp-routing-benchmark

git clone --depth 1 https://github.com/stacklok/toolhive /tmp/toolhive
(cd /tmp/toolhive && go build -o /tmp/thv ./cmd/thv)      # a few minutes
python3 -m venv /tmp/embvenv && /tmp/embvenv/bin/pip install fastembed

THV=/tmp/thv EMBED_PYTHON=/tmp/embvenv/bin/python ./run-semantic.sh bge tokens
THV=/tmp/thv EMBED_PYTHON=/tmp/embvenv/bin/python ./run-semantic.sh hash tokens
```

Report three lines from each run: the `embedding backend:` line, the score line, and
the `embedding requests during run:` line. **If that last number is 0 the semantic
arm never ran and the result is meaningless.**

### Baselines to compare against

| Condition | top-1 | top-3 | top-5 | empty | median |
|---|---|---|---|---|---|
| ToolHive lexical only (FTS5, ratio 0) | 21% | 44% | 49% | 1/43 | 3 ms |
| ToolHive hybrid, **non-semantic control** | 21% | 33% | 44% | 0/43 | 48 ms |
| ToolHive hybrid, **real embeddings** (Run 4) | **44%** | **56%** | **60%** | **0/43** | 76 ms* |

\* Run 4 latency is from a 1.5-CPU container; its own lexical row measured 7 ms
there, so compare latency only within Run 4.

The control row is why the `hash` backend exists: it is a deterministic hashed
bag-of-words with no synonymy by construction —
`cos("refund a charge", "give the money back") = 0.0`. If hybrid-with-`hash` scores
like lexical while hybrid-with-`bge` scores much better, the gain is attributable to
semantics rather than to the hybrid plumbing. Run both; one number alone proves
little.

### What is already proven about the rig

- 412 tools across 14 fixture servers, ground truth validated programmatically.
- vMCP config validates; the OpenAI provider path works.
- **44 embedding requests across 43 queries**, so the semantic arm genuinely calls
  the endpoint. At the time only the model weights were missing; Run 4 supplied them.

Of the three gateways benchmarked, only ToolHive has a semantic mode. MCPProxy is lexical-only in shipped code and
Nexus is Tantivy-only, so this answers "does hybrid beat lexical", not a three-way
comparison.

---

## 6. Gotchas that cost time

**Measurement bugs look like product defects.** Two false results were caught and
corrected mid-run:

- Scoring vMCP at 0% because the scorer did not strip its `{workload}_` tool-name
  prefix. Real answer: 81%.
- Scoring Nexus at 2% with 41/43 empty because its responses are newline-delimited
  JSON objects and the parser only handled a single document. Real answer: 23%,
  later corrected to 28% by the 2026-08-24 scorer audit.

If a gateway scores near zero, suspect `realbench.py::names_in` before believing it.

**Marketing disagrees with source.** MCPProxy advertises hybrid semantic+BM25 with
94% accuracy; a full grep of `internal/` and `cmd/` finds no embedding backend. It
is lexical-only. ContextForge advertises as an AI gateway but has no semantic tool
selection at all. Nexus reads as actively maintained but has had no release since
September 2025.

**`pkill -f <pattern>` matches the shell running it.** Several commands died with
exit 144 mid-run. `restart.sh` and `run-semantic.sh` handle teardown properly; use
them rather than ad-hoc kills.

**Running the harness inside the repo dirties the tree.** `.work/` and
`__pycache__/` were committed by accident once. There is a `.gitignore` now.

**Environment policy is read at session start.** Changing the allowlist has no
effect on a running session. Always start a new one.

---

## 7. Environment facts

| Fact | Value |
|---|---|
| Repo | `Avi-Bendetsky/skills` |
| Branch used | `claude/mcp-tool-calling-layer-9g9q8j` |
| Cloud environments | `env_013GTHpMXmZ2cV2Uz1JPooaQ`, `env_01Rxy9pSf2YduFNNkCTBehHU` — both named "Default", both block `huggingface.co` |
| Rate limit | `seven_day` was at `allowed_warning` — do not spawn probe sessions speculatively |
| Reachable | github.com, pypi.org, npm, crates.io, proxy.golang.org |
| Blocked | huggingface.co, api.openai.com, api.voyageai.com, api.cohere.ai, desktop.docker.com, anthropic.com blog |
| No Docker daemon | client installed, daemon not running |

---

## 8. Resuming

Nothing is outstanding. [`HANDOVER-PROMPT.md`](./HANDOVER-PROMPT.md) is completed
and kept as a record. For optional follow-up work (rank fusion, a larger model,
current ToolHive HEAD), start from "Status" in the validation doc and write a new
protocol file before running anything.
