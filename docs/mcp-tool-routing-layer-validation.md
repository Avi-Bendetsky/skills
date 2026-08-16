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
all unreachable. **These are lexical results only.** See "What is still needed".

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
| **ToolHive vMCP** | **21%** | **42%** | **1/43** | 21% | **44%** | **49%** | **1/43** | 3 ms |
| **MCPProxy** | 2% | 2% | 34/43 | 21% | 30% | 37% | 8/43 | 5 ms |
| **Nexus** | **23%** | 30% | 6/43 | **23%** | 30% | 33% | 6/43 | 6 ms |

### Scale is the story

Top-1 fell from **69–81% at 16 tools to 21–23% at 412** — the same engines, the
same query style. Every lexical engine converges on roughly one-in-five once the
catalogue is realistic. This is the single most important number in this report:
**lexical tool search does not survive a real catalogue.** Any decision made on
16-tool demos, including the earlier run in this document, overstates what these
layers will do for you.

Top-3 is where they still differ, and it matters because the model gets to choose
from what comes back: ToolHive returns the right tool in the top 3 on **44%** of
queries versus 30% for both others.

### MCPProxy collapses without descriptions

MCPProxy went from **2% top-1 with 34/43 empty responses** to 21% with 8 empty
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

Across the full 43 queries the net effect was noise: vMCP 21% → 19%, MCPProxy
21% → 23%, Nexus 23% → 23% top-1.

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
tested.** All five lexical engines failed the same paraphrases, and on the real
412-tool catalogue they all fell to ~21–23% top-1.

## What is still needed to finish this

The lexical half is done and is unambiguous. The semantic half is blocked on
access, not effort — the harness already supports it and ToolHive already
implements it. Any **one** of these unblocks it:

**Recommended: option 2.** A routing layer sees every query anyone ever makes.
Tool descriptions are published schemas and carry little risk, but the *queries*
are user intent, and option 1 ships that intent to a third party on every search
in perpetuity. Options 2 and 3 fetch a model once and then keep all inference
inside the network. Between those, allowlisting one host is far less work than
standing up a container runtime, and the allowlist can be scoped to a single
fetch and closed again afterwards.

1. **An OpenAI-compatible embeddings endpoint.** ToolHive takes
   `optimizer.embeddingProvider: openai` with `embeddingService` +
   `embeddingModel`, and reads the key from `OPENAI_API_KEY` so it never lands in
   config. Cheapest to arrange, but every query leaves the network.
2. **Allowlist `huggingface.co`** at the egress proxy, so `fastembed`/TEI can
   fetch `BAAI/bge-small-en-v1.5` (ToolHive's default). One-time download, then
   fully local inference. This is an organisation policy denial — it needs an
   owner's decision, and should not be worked around.
3. **A Docker daemon plus `ghcr.io`**, letting ToolHive run
   `text-embeddings-inference` locally with no external API. Closest to
   production, heaviest to set up.

Until one of those exists, the honest position is: **on a 412-tool catalogue,
none of these layers routes reliably on lexical search alone.** Choosing on the
strength of the lexical numbers alone would be choosing between 21% and 23%.
