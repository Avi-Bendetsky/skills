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

## Verdict

| # | Project | Abilities | Code quality (measured) | Use it? |
|---|---|---|---|---|
| 1 | **Anthropic tool search** | Server-side deferral, 10k tools, prompt cache preserved, custom ranking via `tool_reference` | Not testable here — it is the mechanism this session runs on | **Yes — default.** Already on. Nothing to operate |
| 2 | **ToolHive vMCP** | 2-tool surface, hybrid BM25+embeddings, identity-filtered retrieval, Starlark code mode, K8s operator | Best measured: 43/43 pass, 86–100% coverage on routing, best accuracy | **Yes — best self-hosted.** Pin the version; optimizer is Experimental |
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

Between the two: **ToolHive** won on every measured axis — accuracy (81% vs 69%),
tool-surface overhead (2 vs 12), and routing-path coverage (86–100%) — at the cost
of a materially heavier config and an Experimental optimizer API. **MCPProxy** is
the better single-binary local story and has security features nothing else has,
but its score threshold returning *nothing* on vocabulary mismatch is the single
riskiest behaviour found in this validation.

And the finding that should drive the decision: **the semantic arm — the thing
that would fix every failure in this benchmark — is exactly what could not be
tested.** All five lexical engines failed the same paraphrases. Before committing
to any of these, run this benchmark against your own tool catalogue with
embeddings actually enabled. The harness is ~150 lines.
