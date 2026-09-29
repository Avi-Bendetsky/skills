# MCP Tool-Routing Layers: Build, Test and Routing-Accuracy Validation

Companion to [`mcp-tool-routing-layer-evaluation.md`](./mcp-tool-routing-layer-evaluation.md).
That document was a source-level read. This one is what happened when the code
was actually built, tested and run.

**Date:** August 2026 · **Environment:** Linux, 4 vCPU, 15 GB RAM, Go 1.24.7,
Python 3.11/3.12, Node 22, Rust 1.94.1.

---

## Method

**Build + test.** Every project was compiled from a fresh clone and its own test
suite executed. Failures were diagnosed individually and attributed to either
the project or the environment — several test failures turned out to be egress
blocks or running as root, and are reported as such rather than held against the
project.

**Live routing benchmark.** Four fixture MCP servers (`payments`, `infra`, `crm`,
`observability`) were written to serve 16 tools with realistic descriptions over
both stdio and streamable HTTP. Each gateway was configured with all four
backends, then asked 16 natural-language questions phrased the way a user would
ask — deliberately avoiding the tool's own vocabulary:

> "give the customer their money back for a card payment" → `refund_charge`
> "bounce a stuck container in the cluster" → `restart_pod`
> "chart the latency numbers over the last hour" → `query_metrics`

This is a deliberately hard set: it isolates the retrieval mechanism by removing
the lexical overlap that would let any keyword matcher succeed. A user typing
"refund a charge" would score far higher everywhere. Read the numbers as a
*relative* ranking of retrieval strategies under vocabulary mismatch, not as an
absolute success rate.

### Two limits on what could be tested

1. **No embedding model.** Model weights could not be downloaded (HuggingFace
   egress blocked, no Docker daemon for the TEI container). Every semantic arm
   therefore went untested end-to-end, including ToolHive's. **The benchmark
   below compares lexical arms only** — ToolHive was run with
   `hybridSearchSemanticRatio: "0.0"`, so its own headline capability is *not*
   what produced its score. Its semantic path is covered by unit tests only.
   *(Partly resolved later: [Run 4](#run-4-semantic-2026-09-29) measured ToolHive's
   semantic arm on the 412-tool catalogue. Other engines' semantic arms and this
   16-tool set remain untested.)*
2. **The registry's NDCG harness could not be run.** See the correction below.

### Correction to the earlier evaluation

The previous document said mcp-gateway-registry ships "a committed ground-truth
dataset". **That is wrong.** `tests/fixtures/search_dataset/` contains only a
README; `unified_dataset.json` and `ground_truth.json` are listed in
`.gitignore:457` and must be generated from your own deployment. The harness is
real and well built — the dataset is bring-your-own, and running it needs a live
registry, MongoDB and an embedding model. That downgrades the claim from
"reproducible published benchmark" to "good harness you must feed yourself".

---

## Routing accuracy (measured)

16 queries, 16 tools, 4 servers. Lexical arms only.

| Gateway | Retrieval engine | Tools exposed | top-1 | top-3 | top-5 | Median latency |
|---|---|---|---|---|---|---|
| **ToolHive vMCP** | SQLite FTS5 + Porter stemming | **2** | **81%** | **94%** | **94%** | 2 ms |
| **MCPProxy** | Bleve BM25, multi-field boosts | 12 | 69% | 69% | 69% | 3 ms |
| **Nexus** | Tantivy fuzzy + BM25 | **2** | 69% | 69% | 75% | 7 ms |
| **Strata** | BM25+ (`bm25s`), field-weighted | 5 | n/a — cannot rank across servers | | | 4 ms |
| **1MCP** (`serve`) | none — passthrough | 16 (all of them) | n/a | | | — |

### What the numbers actually show

**Porter stemming earns its place.** ToolHive's 12-point top-1 lead over the
other lexical engines is the clearest signal in the run. Stemming lets
"paying"→"pay" and "replicas"→"replica" match; Bleve's standard analyzer and
Tantivy's fuzzy terms did not bridge those gaps as reliably.

**MCPProxy's score threshold is a hard failure mode.** Its top-3 is identical to
its top-1 — it never recovers at rank 2 or 3. Three queries returned an **empty
result set**, and passing `limit: 5` changed nothing, confirming a relevance
cutoff rather than a count cap. When BM25 finds nothing above threshold the model
gets nothing back at all. ToolHive always returns its top-N, so a near-miss still
gives the model a second and third candidate. For a routing layer, degrading to
"here are three plausible tools" beats degrading to silence.

**Tool-surface overhead varies 6x.** ToolHive and Nexus expose exactly 2 tools.
MCPProxy exposes 12 (five of them registry/quarantine/profile management). At 16
upstream tools MCPProxy's surface is a net context *loss*; the trade only pays
off in the hundreds.

**Strata cannot route across servers.** Both `discover_server_actions` and
`search_documentation` take a **required** `server_name`/`server_names` argument.
Asked across all four servers, discovery returned all 16 action names *unfiltered
by the query*. Its BM25+ only ranks within one server (3/4 correct on the
payments subset). The model must pick the server first — so Strata is a
schema-deferral layer, not a router. That is a legitimate design, but it is not
what "pick the best MCP for the job" means.

**1MCP's MCP endpoint does not reduce context.** `1mcp serve` passed through all
16 tools verbatim. Its progressive funnel is real and genuinely token-efficient
(`inspect` returns compact CSV-ish rows, no schemas) but it lives in the **CLI**:
`1mcp instructions` → `1mcp inspect <server>` → `1mcp run`. That requires an agent
with shell access using 1MCP's CLI, not an MCP client. For an MCP-level routing
layer, `serve` mode is a straight aggregator.

---

## Build and test results

| Project | Builds | Test result | Attribution |
|---|---|---|---|
| **ToolHive** | ✅ clean | **43/43 vMCP packages pass, 0 failures** | — |
| **MCPProxy** | ✅ clean | all pass | — |
| **1MCP** | ✅ clean | **4,626/4,628 pass** | 2 failures = running as root (`chmod 000` doesn't stop uid 0); verified |
| **Nexus** | ✅ clean (4m46s) | builds; 1 test file in repo | — |
| **agentgateway** | ✅ clean (7m01s) | — | — |
| **Docker MCP Gateway** | ✅ clean | 8 failures | all egress: `desktop.docker.com` → 403 |
| **ContextForge** | ⚠️ Python ≥3.12 only | **~20,500 unit tests run**, 6 failed, 13 collection errors | failures in gRPC/CLI paths; errors are optional deps (`url_normalize`, OPA/Cedar) |
| **mcpjungle** | ❌ `go build ./...` fails | Go unit tests pass | `embed.go: pattern dist: no matching files` — frontend must be built first |
| **hypertool-mcp** | ✅ | 1,087 passed / 2 failed | dormant since 2025-09 |
| **open-strata** | ❌ **broken on fresh install** | with SDK pinned: **8 failed / 61 passed** | see below |
| **MetaMCP** | ✅ installs | **no `test` script exists** | 13 test files, no root runner |
| **Director** | ❌ `pnpm` refused | not run | project requires `bun` |
| **mcp-use** | ✅ | search engine **silently degrades** | `_load_model()` returns `False` on 403 and logs; search then no-ops |

### Coverage on the code that does the routing

Measured with `go test -cover`, ToolHive:

| Package | Coverage |
|---|---|
| `pkg/vmcp/router` | **100.0%** |
| `pkg/vmcp/aggregator` | 92.4% |
| `pkg/vmcp/optimizer/internal/tokencounter` | 92.9% |
| `pkg/vmcp/optimizer/internal/similarity` | 91.6% |
| `pkg/vmcp/optimizer` | 89.9% |
| `pkg/vmcp/optimizer/internal/toolstore` | 86.4% |

MCPProxy: `internal/index` 77.8%, `internal/security/detect` 95.9%,
`internal/security/patterns` 95.9%, `internal/upstream` 20–41% (network code).

### open-strata is broken as published

`pyproject.toml` pins `mcp>=1.0.0` with no upper bound. MCP SDK 2.0.0 renamed
`streamablehttp_client` → `streamable_http_client`, so a clean install fails at
import:

```
ImportError: cannot import name 'streamablehttp_client' from 'mcp.client.streamable_http'
```

Pinning `mcp<2` fixes the import; the suite then still fails 8 of 69 tests
(config-watch, config-sync, HTTP server sync, `get_action_details`,
`execute_action`). Separately, `tests/test_mcp_client.py` raises at **collection**
time unless `GITHUB_PAT` is set, so `pytest tests/` aborts before running
anything. This is consistent with the repo being untouched since 2026-03-25.

### Other operational findings

- **ToolHive's config is heavy.** A minimal working config needs `groupRef`,
  `incomingAuth`, `outgoingAuth`, `aggregation.conflictResolutionConfig` and
  backends — four validation round-trips to get right, versus one JSON file for
  MCPProxy. It does warn correctly that `incomingAuth: anonymous` is
  development-only.
- **Enabling ToolHive's optimizer disables the modern MCP path.** Logged at
  startup: *"MCP 2026-07-28 (Modern) dispatch disabled: enabled features require
  the session (Legacy) path — features: [optimizer]"*. You trade the stateless
  revision for tool search.
- **MCPProxy flags the "lethal trifecta"** in every `retrieve_tools` response
  (`session_risk: {has_destructive_tools, has_open_world_tools, has_write_tools,
  lethal_trifecta, level}`) — prompt-injection exposure surfaced at retrieval
  time. Nothing else tested does this.
- **MCPProxy's read/write/destructive split depends on upstream annotations.**
  Fixtures without MCP hints were all routed to `call_tool_read`, including a
  refund. The safety split is only as good as your upstreams' annotations.
- **Strata retries GET streams in a tight loop** against servers that answer
  `405` to `GET /mcp` (a spec-legal response for POST-only servers).
- **mcp-use enables anonymous telemetry by default** (`MCP_USE_ANONYMIZED_TELEMETRY=false` to disable).
- **Nexus's search takes a keyword array**, not a sentence — the model must
  decompose the query itself.

---

## Run 2: the real catalogue (412 tools, 14 servers)

The 16-tool fixture above is a toy. This run uses **the actual MCP catalogue
connected to this workspace** — 412 tools across Brevo, Canva, ClickUp, Granola,
Hugging Face, Linear, Microsoft 365, Miro, Mobbin, PostHog, Sentry, Supabase,
Vercel and GitHub — with 43 queries whose ground truth was validated against the
catalogue programmatically.

**Embeddings still could not be enabled.** `huggingface.co` is an organisation
policy denial at the egress proxy (`CONNECT tunnel failed, response 403`), and
the proxy's own README instructs that such denials be reported rather than routed
around. There is no Docker daemon for the TEI container, no embedding API key in
the environment, and `api.openai.com`, `api.voyageai.com` and `api.cohere.ai` are
all unreachable. **These are lexical results only.** The semantic arm was measured
later, in [Run 4](#run-4-semantic-2026-09-29).

Tool descriptions could not be enumerated in bulk either — the connectors are
claude.ai-hosted with no local endpoint — so the catalogue was run in two
conditions to bracket the real answer:

- **A — names only:** `description: ""`. The worst case, and what you get from
  servers that ship terse tools.
- **B — tokenised names:** description is the identifier split on `_`/`-`
  ("list pull requests"). This adds **no knowledge** beyond the name; it isolates
  identifier tokenisation from semantics.

Your live connectors have real prose descriptions, so true performance sits at or
above condition B.

| Gateway | A: top-1 | A: top-3 | A: empty | B: top-1 | B: top-3 | B: top-5 | B: empty | Median |
|---|---|---|---|---|---|---|---|---|
| **ToolHive vMCP** | 21% | **42%** | **1/43** | 21% | **44%** | **49%** | **1/43** | 3 ms |
| **MCPProxy** | 2% | 2% | 34/43 | 26% | 37% | 44% | 8/43 | 7 ms |
| **Nexus** | **28%** | 37% | 6/43 | **28%** | 37% | 40% | 6/43 | 7 ms |

> **These numbers were corrected on 2026-08-24.** An audit found the scorer
> over-stripped tool-name prefixes, making 5 of 43 queries unscoreable for
> MCPProxy and Nexus. See [§ Scorer audit](#scorer-audit-2026-08-24). ToolHive was
> never affected; MCPProxy and Nexus were understated by 5-7 points.

### Scale is the story

Top-1 fell from **69–81% at 16 tools to 21–28% at 412** — the same engines, the
same query style. Every lexical engine lands between one-in-five and one-in-four
once the catalogue is realistic. This is the single most important number in this report:
**lexical tool search does not survive a real catalogue.** Any decision made on
16-tool demos, including the earlier run in this document, overstates what these
layers will do for you.

The engines separate differently depending on which number you care about.
**Nexus leads top-1 (28%)** and MCPProxy follows (26%), but **ToolHive leads top-3
(44% vs 37%)** — and top-3 is arguably the number that matters, because the model
chooses from what comes back rather than blindly taking the first hit.

### MCPProxy collapses without descriptions

MCPProxy went from **2% top-1 with 34/43 empty responses** to 26% with 8 empty
purely by tokenising names into the description field. Its Bleve mapping applies
a **keyword analyser** to `tool_name`/`full_tool_name` (exact match only), so a
query like "show me the pull requests waiting on me" cannot reach
`list_pull_requests` through the name at all — it depends entirely on the
description text. ToolHive (FTS5 + Porter over name *and* description) and Nexus
(Tantivy over tokenised name fields) were essentially unchanged between
conditions.

If any of your MCP servers ship thin descriptions, MCPProxy is close to blind on
those tools and will tell you nothing rather than guess.

### Empty results remain the sharpest differentiator

Across 43 real queries ToolHive returned nothing **once**. MCPProxy returned
nothing 8 times in the favourable condition and 34 times in the unfavourable one;
Nexus 6 times. An empty result gives the model no material to reason with, so it
either hallucinates a tool name or gives up. A ranked list that is merely
imperfect is strictly more useful.

### Run 3: do real descriptions rescue lexical search? No.

Condition B used tokenised names because the connectors' real prose could not be
enumerated in bulk. To test whether that understated the engines, one **entire**
server — Supabase, all 29 tools — was enriched with its verbatim live
descriptions while the other 13 servers stayed on condition B. Enriching a whole
server rather than just the correct answers is what keeps this unbiased; describing
only the right answers would hand them extra matching text and rig the result.

The five Supabase queries, rank of the correct tool:

| Query | vMCP B → real | MCPProxy B → real | Nexus B → real |
|---|---|---|---|
| run a SQL query against the database | **1 → 5** | 1 → 1 | 1 → 1 |
| what tables do we have | **2 → MISS** | 1 → 1 | 1 → 1 |
| check the database for security problems | **MISS → 1** | **MISS → 1** | MISS → 5 |
| change the schema safely | MISS → MISS | MISS → MISS | MISS → MISS |
| make typescript types from the schema | 1 → 1 | 1 → 1 | 1 → 1 |

Across the full 43 queries the net effect was small: vMCP 21% → 19%, MCPProxy
26% → 28%, Nexus 28% → 28% top-1. Notably ToolHive's empty-result count fell to
**0/43** with real prose, and MCPProxy's to 6.

Three things worth taking from this:

- **Real prose rescued exactly one query**, and only through literal word overlap:
  `get_advisors` is described as "check for security vulnerabilities", and the query
  said "check the database for security problems". That is not semantics, it is
  matching keywords.
- **Real prose actively hurt ToolHive on two queries.** More text means more
  competing matches: "run a SQL query" fell from rank 1 to 5 because `query_logs`'
  description also contains "SQL query", and "what tables do we have" fell off
  entirely to Miro's `table_create` / `table_list_rows`. Longer descriptions are
  not monotonically better for BM25.
- **"change the schema safely" missed everywhere in every condition.**
  `apply_migration` is described as "Use this when executing DDL operations", and
  no lexical engine connects "schema safely" to "DDL". That is the irreducible gap,
  and it is exactly the gap embeddings exist to close.

**Practical consequence: exporting the real catalogue with descriptions is not
worth anyone's time.** It was measured on a complete server and it does not change
the ranking or the conclusion.

### Reproduce it

`docs/mcp-routing-benchmark/` now contains `real_catalogue.py` (the 412-tool
catalogue and 43 queries), `realsrv.py` (serves any server in either condition)
and `realbench.py` (scores top-1/3/5, empty-rate and latency).

---

## Run 4: semantic (2026-09-29)

**Pre-registered primary result:** with embeddings, ToolHive's top-3 is **56%**,
against **33%** for the non-semantic control (11 queries gained, 1 lost,
p = 0.006). By the pre-registered rule the verdict is **"semantic materially beats
lexical"**. Against pure lexical search, though, the top-3 gain (56% vs 44%) is not
significant (p = 0.18), and it clears the protocol's 10-point bar by a single query.
The clearest effect is on top-1, which doubles from 21% to 44% (p = 0.021). **The
recommendation does not change**: top-3 stays below the 65% bar set before the run.
The motivating failure, "change the schema safely" → `apply_migration`, is still
missed in every condition.

### Method

The protocol, including the matrix, validity gates and verdict thresholds, was
committed and pushed before any score existed:
[`PROTOCOL-run4.md`](./mcp-routing-benchmark/PROTOCOL-run4.md) (commit `c378438`,
analysis script `compare.py` in `ab3199a`). Its matrix, gates and thresholds were
applied unchanged. Corrections and deviations are listed at the end of this Method.

| Item | Value |
|---|---|
| Router | ToolHive vMCP built from `stacklok/toolhive@8343851e` (`vcs.modified=false`, Go 1.26.0; see `mcp-routing-benchmark/results/run4/environment.txt`) |
| Model | `BAAI/bge-small-en-v1.5` via `fastembed` 0.8.1, which serves the quantized ONNX export `Qdrant/bge-small-en-v1.5-onnx-Q@aa8f8b06` (`model_optimized.onnx`, 66,465,124 bytes, sha256 `51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431`), 384 dims. Downloaded once from huggingface.co and then run locally inside the container |
| Catalogue | Unchanged: 412 tools, 14 servers, 43 queries, condition B (tokenised names) unless stated |
| Optimizer | `maxToolsToReturn: 5`, `hybridSearchSemanticRatio: "0.6"` (the protocol value; ToolHive's own defaults are 0.5 and 8 slots), local OpenAI-compatible `embedserver.py` |
| Host | Linux container (Debian 12, Python 3.11.2), capped at 1.5 CPU / 1.2 GB, on the owner's **remote** Docker host (Hetzner, reached over Tailscale; the currently selected Docker context `neko`), which was also running other services |

**Where it ran, and why that is not a policy workaround.** The blocker in Runs 1-3
was the Claude Code cloud environments' egress policy. Run 4 did not change or
bypass that policy. It ran on the owner's own Docker host, where huggingface.co
answered directly. The model came from huggingface.co itself: no mirror and no
substitute model. Embedding inference ran inside the benchmark container against a
localhost endpoint. That holds by the rig's design and was not independently
monitored; no query went to a third-party embedding API. On authorization: the
owner's instruction was to continue the handover. The owner was told in the session
that the runs were going to `neko`, with an offer to stop, and did not object. No
separate, explicit authorization to run outside the cloud environment was
recorded.

**Corrections and deviations.**

- The protocol dates the provenance window to PR #3 (2026-08-16 03:25Z). Run 3 was
  actually published in PR #4 (03:33Z). The claim still holds, because the next
  ToolHive `main` commit after `8343851e` is `a3540917` at 2026-08-17 19:04Z. The
  build used for Runs 1-3 was never recorded, and the ToolHive rows were
  re-measured during the scorer audit (dated 2026-08-24, committed 2026-08-27),
  also on an unrecorded build.
  **Build parity therefore rests on R0 and R2 reproducing the published rows
  exactly** (below), not on a recorded commit.
- The recommendation bar "top-1 ≥ 42% (≥ 18/43, double the ceiling)" is slightly
  inconsistent: 18/43 is 41.9%, and 42% is double ToolHive's own 21%, not double
  the 28% cross-engine lexical best. R1's 19/43 (44.2%) meets both the percentage
  and the count form.
- The harness line meant to record the `thv` version printed ToolHive's "local
  build" banner instead, in every `stdout.txt`. Gate 5 was verified separately, and
  the full version and embedded build info are in
  `mcp-routing-benchmark/results/run4/environment.txt`.
  The line is fixed for future runs.

### Results

Every row passed every validity gate: the requested backend loaded, all 43 queries
completed with 0 errors, and every row with ratio > 0 made 44 embedding requests
(one batch for the 412-tool index plus one per query).

| Row | Embedder | Fixtures | Ratio | top-1 | top-3 | top-5 | empty | median | embed requests |
|---|---|---|---|---|---|---|---|---|---|
| R0 | hash | tokens | 0.0 | 21% | 44% | 49% | 1/43 | 7 ms | 1 (index only) |
| **R1** | **bge** | **tokens** | **0.6** | **44%** | **56%** | **60%** | **0/43** | 76 ms | 44 |
| R2 | hash | tokens | 0.6 | 21% | 33% | 44% | 0/43 | 56 ms | 44 |
| R3 | bge | real | 0.6 | 44% | 56% | 60% | 0/43 | 76 ms | 44 |
| R4 | hash | real | 0.6 | 19% | 30% | 44% | 0/43 | 57 ms | 44 |
| R5 | bge | tokens | 1.0 | 44% | 56% | 60% | 0/43 | 74 ms | 44 |

R1 and R2 were each run twice. The repeats are identical query for query, so the
rig is deterministic. With 43 queries the uncertainty is wide: 95% Wilson intervals
are 30-59% for R1 top-1 and 41-70% for R1 top-3. Only these per-row intervals are
reported; no interval was computed for the paired differences. Latency is comparable within this
table only, because the container ran on a smaller, shared host.

**The build matches the published baselines.** R0 reproduces the published lexical
row exactly (21/44/49%, 1/43 empty), and R2 reproduces the published non-semantic
control exactly (21/33/44%, 0/43). Raw `find_tool` responses for R0 and R1 were
checked by hand against what `realbench.py::names_in` parses from them: same tools,
same order. The transcripts are in `mcp-routing-benchmark/results/run4/R0/probe.txt`
and `mcp-routing-benchmark/results/run4/R1a/probe.txt`.

### Paired comparison

Exact two-sided McNemar test, paired per query ("gained" = right in the first row,
wrong in the second). The p-values are unadjusted.

| Comparison | top-1 | top-3 | top-5 |
|---|---|---|---|
| **R1 bge vs R2 hash control** (pre-registered primary) | 44% vs 21%, 11 gained / 1 lost, p = 0.006 | **56% vs 33%, 11 / 1, p = 0.006** | 60% vs 44%, 7 / 0, p = 0.016 |
| R1 bge vs R0 pure lexical | 44% vs 21%, 13 / 3, p = 0.021 | 56% vs 44%, 7 / 2, p = 0.18 | 60% vs 49%, 6 / 1, p = 0.125 |
| R3 bge vs R4 hash, both with real Supabase prose (additional) | 44% vs 19%, 12 / 1, p = 0.003 | 56% vs 30%, 13 / 2, p = 0.007 | 60% vs 44%, 7 / 0, p = 0.016 |

How to read these:

- **R1 vs R2 shows the hybrid plumbing is not the cause of the gain.** It overstates
  the size of the semantic effect, though. R2's top-3 slots come from a hashed
  bag-of-words embedder that is dominated by hash collisions and ties (tools with
  no shared tokens all sit at cosine distance 1.0, and ToolHive's unstable
  `sort.Slice` orders those ties by sort mechanics, not relevance). So
  R2 is a noisy non-semantic ranker, and it scores *below* pure lexical on top-3
  (33% vs 44%).
- **R1 vs R0 is the fair measure of magnitude.** Top-1 improves by 13 queries to 3
  (p = 0.021). Top-3 improves by 7 to 2, which is not significant.
- **Multiple comparisons.** Across the four pre-registered tests (R1 vs R2 and R1
  vs R0, each on top-1 and top-3), the top-1 result against R0 survives a Holm
  correction (0.021 < 0.025) but not Bonferroni (0.0125).
- **How close the verdict is.** It needs R1 top-3 at least 10 points above R0. The
  margin is 5 queries (11.6 points); 4 queries would have given "directional
  improvement, not established".

Queries bge gets into the top 3 that pure lexical does not: "who can write to this
repository", "have the AI figure out the root cause of this crash", "how much
traffic did the site get", "combine these two duplicate tasks", "turn on my out of
office", "text message blast to customers" and "draw a flowchart on the
whiteboard". These are the vocabulary-mismatch paraphrases this benchmark was built
to test. Queries it loses from the top 3: "what did CI say about the failing job"
(lexical rank 1 → rank 4) and "ship this to production" (rank 2 → rank 5).

### How ToolHive's "hybrid" search actually works

R5 (ratio 1.0) has the same top-3 as R1 (ratio 0.6) on all 43 queries. That looked
like a harness fault, so the ToolHive source at `8343851e`
(`pkg/vmcp/optimizer/internal/toolstore/sqlite_store.go`) was read.
`hybridSearchSemanticRatio` does **not** blend BM25 and cosine scores:

- **Slots, not scores.** `hybridSearchLimits` gives the semantic arm
  `round(maxToolsToReturn × ratio)` slots and FTS5 the rest. With 5 slots that is
  3 + 2 at ratio 0.5-0.6, 4 + 1 at 0.7-0.8, and 5 + 0 at 0.9-1.0. At 5 + 0 FTS5 is
  not queried at all.
- **Semantic results first.** `mergeResults` lists all semantic results first,
  then appends FTS5 results not already present.
- **No refill.** FTS5 fetches only its own slot count before deduplication, and
  overlaps are not refilled. Lists can therefore be shorter than 5 (both R1 probe
  queries return 4 tools), and at ratio 0.6 a tool at BM25 rank 3 or lower can
  never appear through the lexical arm (it can still come in through the semantic
  arm). "look through my email" goes from BM25 rank 4 to a miss this way.
- **Distance filter.** Semantic hits with cosine distance above 1.0 (negative
  similarity) are dropped.
- **Keyword stop-list.** The keyword arm silently drops 23 words, including
  `schema`, `table`, `text`, `data`, `key`, `index` and `id`. "Pure lexical" here
  therefore means BM25 behind ToolHive's stop-list.

Consequences, inferred from the source (the per-query count from each arm was not
logged):

- At any ratio of 0.5 or above with 5 slots, all three top slots are semantic. That
  is why R5 and R1 have identical top-3 lists. Their top-5 hit/miss differs on 4
  queries (2 gained, 2 lost): at ratio 1.0 ranks 4-5 are semantic too.
- A tool that only BM25 ranks highly (outside the semantic top three) can reach the
  top three only below ratio 0.5, at the cost of a semantic slot. That
  configuration was not measured.

### Real descriptions change little, on a small test

R3 serves Supabase's verbatim live descriptions. That changes 29 of the 412 tools,
and only 5 of the 43 queries target Supabase, so this tests little. Top-1 and
top-3 hit/miss are unchanged on all 43 queries. On top-5 one query gains ("check
the database for security problems", miss → rank 4, through a lexical slot) and one
loses ("ship this to production", rank 5 → miss), so top-5 stays at 26/43. The
top-3 lists themselves change on 5 queries, including a GitHub and a Sentry query
where a Supabase tool dropped out or moved down once its real description was used.
The hash control with the same real prose (R4) ranks `get_advisors` first for the
security query, through literal word overlap ("security"), while bge reaches it only
at rank 4. Across all 43 queries, R3 still beats R4 by a wide margin (table above).

The wiring is sound: ToolHive embeds `name: … description: …`, so the descriptions
do reach the embeddings. This is a small null result, not a wiring fault.

### The motivating example is still missed

"change the schema safely" → `apply_migration` missed in **every** row: with and
without embeddings, with tokenised names and with the real "Use this when executing
DDL operations" description.

- With tokenised names (R1), bge's top three were
  `update_project_deployment_protection`, `section_update_metadata` and
  `table_update_view`.
- With real descriptions (R3), they were `update_project_deployment_protection`,
  `reset_branch` and `section_update_metadata`.
- On the keyword side, ToolHive's stop-list removes "schema", so the lexical arm
  only ever saw "change … safely".

Semantics closes many vocabulary gaps in this benchmark, but not this one. Even with
embeddings, 19 of 43 queries still miss the top 3, and 17 miss the top 5.

### Limits of this run

- **Sample.** 43 hand-written queries on one catalogue, clustered by server (github
  7, several servers 5). The p-values assume the queries are exchangeable and do not
  account for that clustering. One query is 2.3 points.
- **Model.** One model, and a quantized ONNX build of it. A larger or full-precision
  model, for example ToolHive's TEI default, was not tested.
- **Engines.** Of the three gateways benchmarked (ToolHive, MCPProxy, Nexus), only
  ToolHive has a semantic mode. mcp-gateway-registry (FAISS with reciprocal rank
  fusion) and mcp-use also do semantic retrieval but were not run. Anthropic's
  server-side tool search is not testable from this harness.
- **Version.** Pinned to the August build. ToolHive's optimizer has changed since
  (for example `fe39aecf`, which reuses tool embeddings across sessions); current
  HEAD was not re-measured.
- **Host.** Remote and shared, so latencies are indicative only.

### What it changes

- **The recommendation stands, as pre-registered:** Anthropic's tool search for
  selection, and ToolHive or MCPProxy only for running, authenticating and isolating
  MCP servers. The bar for recommending a self-hosted router for selection was
  top-1 ≥ 42% **and** top-3 ≥ 65%. Top-1 clears it by one query; top-3 (56%, 95%
  interval 41-70%) does not. Two user requests in five still get nothing correct in
  their top five.
- **Among the three gateways benchmarked**, ToolHive with embeddings has the
  highest measured accuracy: 44% top-1 / 56% top-3, against MCPProxy's 26% / 37% and
  Nexus's 28% / 37% (lexical-only, Run 2). This is a cross-run comparison. It is
  unpaired and not significance-tested, because Run 2's per-query outputs for
  MCPProxy and Nexus were not kept. That results carry across hosts is shown only
  for ToolHive's own rows (R0 lexical and R2 hash control).
- **If you use ToolHive's optimizer for selection anyway**, enable the semantic
  arm. The earlier "MCPProxy leads on top-1" holds only with it off.
- **Named follow-up, only if self-hosted selection is still wanted:** rank fusion
  (for example reciprocal rank fusion) instead of semantic-first slot splitting, so
  a tool that only BM25 ranks highly can still reach the top three. Test it together with a
  larger embedding model.

Reproduce: build `thv` from `stacklok/toolhive` at
`8343851e8a58086ff0768cd35856e14b11d273fd` (a full clone, not `--depth 1`; Go 1.26
via `GOTOOLCHAIN=auto`) and install `fastembed==0.8.1`.
`docs/mcp-routing-benchmark/PROTOCOL-run4.md` has the matrix;
`SEMANTIC_RATIO=<r> ./run-semantic.sh <bge|hash> <tokens|real>` runs a row; the
per-row outputs, probe transcripts and environment record are in
`docs/mcp-routing-benchmark/results/run4/`; and
`python3 compare.py results/run4/R1a/score.txt results/run4/R2a/score.txt`
reproduces the paired test.

## Verdict

| # | Project | Abilities | Code quality (measured) | Use it? |
|---|---|---|---|---|
| 1 | **Anthropic tool search** | Server-side deferral, 10k tools, prompt cache preserved, custom ranking via `tool_reference` | Not testable here — it is the mechanism this session runs on | **Yes — default.** Already on. Nothing to operate |
| 2 | **ToolHive vMCP** | 2-tool surface, hybrid BM25+embeddings (semantic-first slot split, not score fusion), identity-filtered retrieval, Starlark code mode, K8s operator | Best measured: 43/43 pass, 86–100% coverage on routing; with embeddings 44% top-1 / 56% top-3 on 412 tools (Run 4), the highest of the three gateways benchmarked (cross-run, not significance-tested) | **Yes — best self-hosted.** Pin the version; optimizer is Experimental. If used for selection, enable the semantic arm |
| 3 | **MCPProxy** | `retrieve_tools` + read/write/destructive split, quarantine, scanners, trifecta detection, single binary | Builds clean, all pass, 78–96% coverage on index/security | **Yes, with eyes open.** Lexical-only; empty results on vocabulary mismatch |
| 4 | **1MCP** | Progressive CLI funnel, presets/filters, per-session template servers | 4,626/4,628 pass — cleanest TS suite tested | **Only for CLI agents.** `serve` gives no context reduction |
| 5 | **mcp-gateway-registry** | FAISS + RRF, NDCG harness, enterprise OAuth | Could not run — needs live registry, MongoDB, embeddings | **Only if you'll run the eval.** BYO dataset; heaviest deploy |
| 6 | **ContextForge** | Federation, virtual servers, ~40 plugins, multi-tenancy | ~20.5k tests, 6 real failures; Python ≥3.12 | **Yes as governance, no as router.** No tool search |
| 7 | **agentgateway** | CEL per-tool authz, multiplexing, OTel, xDS | Builds clean | **Yes as policy plane, no as router.** No search |
| 8 | **Docker MCP Gateway** | Container isolation, catalog `mcp-find`, secrets | Builds clean; failures all environmental | **Only if Docker-centric.** Searches the catalog, not your tools |
| 9 | **Nexus** | 2-tool surface, Tantivy search, LLM routing, RBAC | Builds clean; ~1 test file; **no release since 2025-09** | **No.** Good design, unmaintained |
| 10 | **Composio Tool Router** | 500+ integrations, hosted, session-scoped URLs | Not self-hostable; May 2026 breach (5,241 API keys, 5,001 GitHub OAuth tokens) | **Only if credentials are low-value** |
| — | **open-strata** | 5-tool progressive surface, field-weighted BM25+ | **Broken on fresh install**; 8/69 fail when patched; cannot route across servers | **No.** Use Klavis hosted instead |
| — | **MetaMCP** | Namespaces, middleware, inspector | **No test script**; 13 test files | **No** for production |
| — | **MCPJungle** | Tool groups, team gateway | Go tests pass; `go build ./...` fails without prebuilt frontend | **No** as a router — static curation only |
| — | **Director** | Playbooks, OAuth, filtering | Requires `bun`; single-author; AGPL | **No** |
| — | **hypertool-mcp** | Curated toolsets | 1,087 pass / 2 fail — but dormant 11 months | **No** |
| — | **mcp-use** | `ToolSearchEngine` (fastembed + cosine), `ServerManager` | Search silently no-ops without model access; telemetry on by default | **Reference only** — it's an agent library, not a layer |

### Bottom line

Nothing changed at the top: **use Anthropic's tool search, and add ToolHive vMCP
or MCPProxy only for what it cannot do** — running, authenticating, isolating and
governing many MCP servers.

That recommendation is the one pre-registered for Run 4, and Run 4 did not meet the
bar to change it. Between ToolHive and MCPProxy, choose on operations. **ToolHive**
has the lower empty-result rate, 86–100% routing-path coverage and a 2-tool surface
against 12, at the cost of a materially heavier config and an Experimental
optimizer API. **MCPProxy** is the better single-binary local story and has
security features nothing else has, but its score threshold returning *nothing* on
vocabulary mismatch is the single riskiest behaviour found in this validation.

If you use one of them for selection anyway: with its semantic arm on, ToolHive has
the highest accuracy measured here, 44% top-1 / 56% top-3 against MCPProxy's
26% / 37%. That comparison is across runs and not significance-tested. It also
costs a local embedding service and about 70 ms more per search on the test
container. With the semantic arm off, the Run 2 split holds: MCPProxy leads top-1
(26% vs 21%) and ToolHive leads top-3 (44% vs 37%).

And the finding that should drive the decision: **semantic search helps a lot, but
not enough to replace Anthropic's tool search.** On the real 412-tool catalogue the
lexical engines fell to 21–28% top-1; embeddings lift ToolHive to 44% top-1, yet
two requests in five still get nothing correct in the top five, and the
schema-migration paraphrase that motivated the semantic test is still missed. See
[Run 4](#run-4-semantic-2026-09-29).

## Status

**Finished.** The semantic half, blocked in Runs 1-3 by the cloud environment's
`huggingface.co` policy denial, was measured in
[Run 4](#run-4-semantic-2026-09-29) on the owner's own Docker host, where the model
could be fetched once from huggingface.co and then run locally inside the
benchmark container. No query went to a third-party embedding API.

Optional follow-ups, none required for the conclusion:

1. **Rank fusion instead of slot splitting.** Merge BM25 and cosine ranks (for
   example reciprocal rank fusion) so a tool that only BM25 ranks highly can still
   reach the top three. Needs a ToolHive change or a harness-side reranker. Setting
   the ratio below 0.5 also gives BM25 a top-three slot, at the cost of a semantic
   slot; that was not measured.
2. **A larger or full-precision embedding model**, for example ToolHive's TEI
   default, to see whether the 56% top-3 moves.
3. **Re-measure on current ToolHive HEAD.** The optimizer has changed since the
   pinned `8343851e`.

---

## Scorer audit (2026-08-24)

The harness was re-read line by line after the fact, on the principle that numbers
someone may act on deserve an adversarial pass. Four defects were found; two
changed published results.

**1. Prefix over-stripping — changed the numbers.** `strip_prefix` removed a
separator-qualified prefix (`Server:tool`, `Server__tool`) *and then* an
underscore-qualified one. Every ClickUp tool is itself named `clickup_*`, so
`ClickUp:clickup_create_task` became `create_task` and never matched its ground
truth. **5 of 43 queries were permanently unscoreable for MCPProxy and Nexus.**
ToolHive was unaffected, because its `{workload}_` prefix matches on original
casing first and returns before the lowercase candidate is tried — which is exactly
why the bug survived: it produced plausible numbers for the tool being examined
most closely. Fixed by splitting off exactly one qualifier.

**2. Server-blind matching — inflated 2 queries.** Ten tool names in this catalogue
exist on more than one server (`list_projects`, `search_issues`, `list_issues`, …).
The scorer compared bare tool names, so a gateway answering GitHub's
`search_issues` to "what is crashing in production right now" scored as correct
when Sentry was intended. Now scored on `(server, tool)`, with the server checked
whenever the gateway reports one.

**3. Errors counted as empty results.** A JSON-RPC error and a genuine no-match
both produced an empty ranked list, so a protocol failure would silently inflate
the empty-result metric — the metric this report leans on most. Now counted and
reported separately. **Re-running every condition showed 0 errors across all three
gateways, so the previously published empty-result counts were genuine.**

**4. `run-semantic.sh` masked failures.** The scoring step is piped to `tail`, and
without `pipefail` a crashed run exited 0. Observed live: a failed `bge` run
reported success. Fixed with `set -o pipefail`.

**Net effect.** ToolHive's numbers are unchanged. MCPProxy rose from 21% to 26%
top-1 and 30% to 37% top-3; Nexus from 23% to 28% and 30% to 37%. The
qualitative conclusions survive — lexical routing still collapses at real
catalogue scale, descriptions still do not rescue it, and ToolHive still has by far
the lowest empty-result rate — but **"ToolHive won every measured axis" was wrong
and has been retracted.**

The general lesson is the one already in this document: on this harness, a
surprising score is more often the scorer than the product. It has now been true
three times.
