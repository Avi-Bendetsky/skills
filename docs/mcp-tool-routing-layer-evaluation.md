# MCP Tool-Routing Layer: Top 10 Options

**Question evaluated:** a layer that sits between many MCP servers and the model's
context window, exposing only a small surface, and selecting the right tool/server
per request — so thousands of MCPs can be installed without flooding context.

**Method:** every candidate below was cloned and read at source level (retrieval
implementation, tool surface, test/CI posture, commit recency). Claims from
project marketing were checked against the code; where they disagree, the code
wins and the disagreement is noted.

**Research date:** August 2026.

---

## Reality check, first

Three things worth internalising before picking anything:

1. **"Thousands of MCP servers" is not a tested regime anywhere.** The tested
   regime everywhere is *hundreds to thousands of **tools*** drawn from *tens of
   servers*. Anthropic's server-side tool search is the only implementation with a
   published, enforced 10,000-tool ceiling. Every self-hosted gateway below has to
   connect to each upstream and call `tools/list` to build its index — 1,000 stdio
   servers means 1,000 processes. Plan for tens-to-low-hundreds of servers and
   thousands of tools; that is where the engineering actually is.

2. **Retrieval quality is the whole product, and most projects do not measure it.**
   Exactly two of the projects reviewed ship a retrieval evaluation harness in CI
   (MCPProxy, mcp-gateway-registry). The rest ship a search box and hope. If the
   layer picks the wrong tool, you have traded a context problem for a correctness
   problem — a strictly worse trade.

3. **Aggregation ≠ routing.** Most "MCP gateways" — including the biggest, most
   enterprise-ready ones — do *static curation*: you hand-group tools into named
   virtual servers and point clients at one. That reduces context by making *you*
   choose in advance. It is not a layer that picks the best MCP for the job. This
   evaluation separates the two categories explicitly, because the marketing does not.

---

## The four architectures

| Family | How context stays small | Examples |
|---|---|---|
| **A. Model-native deferral** | Tool defs withheld server-side; model searches a catalog and loads 3–5 defs on demand | Anthropic tool search tool |
| **B. Routing proxy** | Proxy exposes ~2–7 meta-tools (`find_tool`/`call_tool`); real tools live behind an index | ToolHive vMCP, MCPProxy, mcp-gateway-registry, Strata, Nexus, 1MCP |
| **C. Governance gateway** | Static curation + policy; context reduced by hand-scoping | ContextForge, agentgateway, Docker MCP Gateway |
| **D. Hosted router** | Vendor runs B for you across their integration catalog | Composio Tool Router/Rube, Klavis, Arcade |

A and B compose well (B handles process/auth/governance, A handles selection).
C is a layer *under* A or B, not a substitute. D trades operational work for
credential centralisation — see the Composio entry for what that costs.

---

## The top 10

### 1. Anthropic tool search tool — *the default if you are on Claude*

`tool_search_tool_bm25_20251119` / `tool_search_tool_regex_20251119`, GA on the
Claude API; on by default in the Claude Agent SDK and Claude Code.

- **How it works:** you send all tool definitions with `defer_loading: true`. Deferred
  definitions are excluded from the system-prompt prefix, so **prompt caching is
  preserved**. Claude searches names, descriptions, argument names and argument
  descriptions; the API returns `tool_reference` blocks and expands them inline.
- **Scale:** 10,000 deferred tools per request; 5 results per search by default,
  `limit` settable 1–10,000.
- **Applies to MCP:** set `defer_loading` once on an `mcp_toolset`'s `default_config`
  rather than per tool.
- **Escape hatch that matters:** you can implement **your own** search (embeddings,
  reranking, anything) by returning `tool_reference` content blocks from an ordinary
  custom tool. You get the context-window mechanics for free and keep full control of
  ranking. This is the single most under-used capability in this whole space.
- **Reported effect:** ~55k tokens of definitions for a GitHub+Slack+Sentry+Grafana+Splunk
  setup, reduced by >85%.
- **Limits:** Claude-only. Not available on Microsoft Foundry deployments hosted on
  Azure, or Bedrock's Converse API (InvokeModel only). Disabled by the SDK when
  `ANTHROPIC_BASE_URL` points at a non-first-party proxy. Does **not** run, authenticate,
  isolate or govern MCP servers — it only solves selection.

**Verdict:** battle-tested by definition — it is the mechanism this session is
running on. If you are on Claude, start here and only add a proxy for the things
it explicitly does not do.

---

### 2. ToolHive vMCP + MCP Optimizer (Stacklok) — *best self-hosted router*

Apache-2.0, Go. `github.com/stacklok/toolhive`, `pkg/vmcp/`.

- **Tool surface:** with the optimizer on, vMCP exposes exactly two tools —
  `find_tool` and `call_tool`.
- **Retrieval — genuinely hybrid, verified in source:** SQLite store with an FTS5
  virtual table using **Porter stemming** for the lexical arm, plus float32 embeddings
  (BLOB) for the semantic arm, from either a TEI server or any OpenAI-compatible
  embedding endpoint. `hybridSearchSemanticRatio` splits the result budget between
  arms; `semanticDistanceThreshold` and `maxToolsToReturn` (1–50) bound the output.
  The lexical arm falls back from explicit keywords to description terms when every
  keyword is too common to discriminate — a thoughtful detail.
- **Security:** `Search()` takes an `allowedTools` list, so retrieval is filtered by
  the caller's identity, not just execution. The embedding API key is read from the
  environment specifically so it never lands in a CRD or ConfigMap.
- **Code mode:** `execute_tool_script` runs Starlark; inner tool calls route back
  through the core's `CallTool` so **each call is re-authorised by its real name**.
  Bounded by `ParallelMax` and `ToolCallTimeout` with explicit guards against the
  zero-value "unlimited"/"no deadline" traps.
- **Robustness posture:** 1,011 test files, 29 CI workflows, K8s operator with CRDs,
  Kubernetes-native embedding-server controller, LRU+TTL caching aggregator, conflict
  resolvers (prefix/priority/manual), speaks the MCP 2026-07-28 stateless revision and
  bridges era-mismatched client×backend pairs.
- **The caveat, from their own stability table:** `pkg/vmcp/optimizer` is marked
  **Experimental** — "tier API may evolve". So is `pkg/vmcp/composer` and
  `pkg/vmcp/cli`. The surrounding vMCP is a shipped product; the optimizer specifically
  is not API-frozen. Pin your version.

**Verdict:** the most complete self-hosted implementation of what you asked for, and
the only one combining true hybrid retrieval, per-identity retrieval filtering,
container isolation and a sandboxed code mode. Best pick if you want to run this yourself.

---

### 3. MCPProxy (smart-mcp-proxy/mcpproxy-go) — *best-engineered single binary*

MIT, Go, single cross-platform binary with embedded web UI. Active (HEAD 2026-08-13).

- **Tool surface:** `retrieve_tools` for discovery, then **split execution tools** —
  `call_tool_read`, `call_tool_write`, `call_tool_destructive`, with each retrieval
  result carrying a `call_with` field naming its variant. Making blast radius part of
  the tool surface is a design idea nobody else here had.
- **Retrieval:** Bleve BM25 with per-field analyzers (keyword for names/servers,
  standard for description/params/tags) and a boosted boolean query mixing exact,
  prefix, wildcard and match clauses.
- **Correction to their marketing:** the site advertises a hybrid semantic+BM25 result
  (94% vs 34% accuracy, March 2026 blog). **That is not in the shipped code.** A full
  grep of `internal/` and `cmd/` finds no embedding backend — the only `embedding` hits
  are a tokenizer model table and unrelated prose. Treat it as lexical-only today.
- **Robustness posture — the strongest in the field:** 656 test files, 26 CI workflows
  including CodeQL, OpenSSF Scorecard, e2e, benchmarks, and an **`eval.yml` retrieval
  regression gate** over frozen datasets with a pinned external eval repo and a nightly
  live soak, split into a blocking deterministic security scorer and a report-only
  network-dependent retrieval job. That is real evaluation discipline.
- **Security:** new servers are quarantined until manually approved (tool-poisoning
  defence), with pluggable Docker-based scanners (Snyk, Semgrep, Trivy, Cisco)
  normalised to SARIF with a composite risk score; plus `toolsig` change detection and
  a sandbox package.
- **Operational fit:** bbolt storage, reconnect-on-use for upstreams, profiles, OAuth,
  code-execution mode, macOS menu-bar app.

**Verdict:** if I had to bet on one OSS project in this space on engineering rigour
alone, this is it. Choose it over ToolHive when you want a local-first single binary
and lexical search is enough; choose ToolHive when you need Kubernetes, hybrid
semantic retrieval, or per-identity retrieval filtering.

---

### 4. agentic-community/mcp-gateway-registry — *best retrieval science*

Apache-2.0, Python + React. Very active (hundreds of commits in the clone window).

- **Retrieval:** semantic search over sentence-transformer embeddings with FAISS,
  fused with a lexical arm via **Reciprocal Rank Fusion** (RRF, k=60).
- **What sets it apart:** `scripts/evaluate_search.py` is a self-contained
  **NDCG@10 harness** with a committed ground-truth dataset, comparing RRF against the
  legacy scorer offline using the same scoring code as production. Of everything
  reviewed, only this and MCPProxy treat retrieval quality as a measurable regression
  surface.
- **Surface:** `search_registry` (the old `intelligent_tool_finder`, deprecated and
  scheduled for removal in v1.26.0 — note the churn), returning ranked tools with an
  optional discovery receipt describing what was exposed vs withheld.
- **Enterprise:** OAuth with Keycloak/Entra/Cognito/PingFederate, telemetry collector,
  metrics service, Terraform.
- **Cost:** heaviest deployment here — registry, frontend, metrics service, auth
  server. Not a drop-in local binary.

**Verdict:** pick this when retrieval accuracy across a large catalogue is the
dominant risk and you have the ops capacity for a multi-service deployment.

---

### 5. 1MCP (`@1mcp/agent`) — *best progressive-navigation approach*

TypeScript/npm, Apache-2.0. Very active (HEAD 2026-08-14), 406 test files, 8 CI
workflows incl. CodeQL.

- **Approach:** rejects ranked search in favour of a three-step CLI-mode funnel —
  `instructions` → `inspect <server>` → `run`. The agent navigates from intent to
  server to tool, pulling schemas only at the last step.
- **Also offers:** static servers loaded at startup vs template servers created per
  client/session, presets and filters, instruction aggregation, stdio proxy and
  streamable HTTP paths.
- **Trade-off:** navigation costs extra round-trips and depends on server-level naming
  being legible to the model; it degrades more gracefully than bad search but has a
  lower ceiling than good search. No relevance ranking means no way to tune recall.

**Verdict:** the strongest non-search option, and the easiest to reason about when it
misbehaves. Good fit if you distrust retrieval quality and prefer deterministic navigation.

---

### 6. Klavis Strata (`open-strata`) — *progressive discovery, benchmarked*

Python, `pipx install strata-mcp`. Apache-2.0.

- **Surface:** five tools — `discover_server_actions`, `get_action_details`,
  `execute_action`, `search_documentation`, `handle_auth_failure`. The last one is
  unusual and welcome: auth failure is a first-class, recoverable state rather than a
  dead end.
- **Retrieval:** BM25+ via `bm25s` with PyStemmer, implemented **field-aware** — each
  field is scored as its own document and scores are recombined per tool with per-field
  weights. That is a better default than concatenating fields into one blob.
- **Published results (vendor, hosted version):** +15.2% pass@1 over the official
  GitHub MCP server and +13.4% over Notion on MCPMark; ~60% context reduction.
- **Caveat that matters:** the OSS repo is the "streamlined version" and
  `open-strata/` has not been touched since **2026-03-25**. The actively developed
  product is the hosted service. Judge this as a hosted option with an OSS demo, not
  as maintained OSS.

**Verdict:** best-articulated progressive-discovery design with real benchmark numbers.
Use the hosted product, or fork the OSS knowing you own it.

---

### 7. Nexus (Nexus-Router, ex-Grafbase) — *good design, dormant*

Rust, Apache-2.0.

- **Retrieval:** Tantivy index with `DisjunctionMaxQuery` over fuzzy term queries and
  boosts across tool title, name, server name, description and input params — a clean,
  fast, dependency-free lexical design. Clean `search` + `execute` two-tool surface,
  with OTel spans for `mcp.search.keywords` and `mcp.execute.target_tool`.
- **Also:** LLM provider routing (OpenAI/Anthropic/Google/Bedrock), RBAC on MCP tools,
  Redis-backed rate limiting, TOML config.
- **Disqualifying caveat:** **no commits since 2025-10-21; last release 0.6.0 on
  2025-09-29** — roughly ten months dormant. The clone contains one test file.
  Secondary sources describing it as "actively maintained" are wrong; the git history
  is unambiguous.

**Verdict:** worth reading for the design; do not build on it without adopting maintenance.

---

### 8. IBM ContextForge (`mcp-context-forge`) — *governance, not routing*

Apache-2.0, Python. **v1.0.7** — one of the few genuinely GA products here. 721 test
files, 29 CI workflows, 17 recent authors.

- **What it is:** federation and governance for MCP/A2A/REST/gRPC behind one endpoint —
  virtual servers, retries, rate limiting, user-scoped OAuth, multi-tenancy, a large
  plugin system (~40 plugins: PII guard, content moderation, schema guard, circuit
  breaker, caching, TOON encoding, VirusTotal, OPA-style unified PDP).
- **What it is not:** a semantic router. Grepping `mcpgateway/` for semantic or
  embedding-based tool selection returns nothing but unrelated prose. Context reduction
  here is **manual curation** — you build virtual servers by hand and point each client
  at the right one.

**Verdict:** the strongest governance/federation layer in the ecosystem, and the wrong
tool for automatic selection. Correct use: ContextForge underneath, Anthropic tool
search (option 1) on top.

---

### 9. agentgateway — *the policy data plane*

Apache-2.0, Rust. Active (HEAD 2026-08-13), 16 recent authors, 132 test files, xDS-based.

- **What it does:** MCP and A2A multiplexing with per-tool authorization expressed in
  **CEL** — e.g. `mcp.tool.name == "increment" && jwt.groups == "admin"` — plus
  guardrails, OTel metrics/logging with `gen_ai.tool.name` attributes, JWT enforcement.
- **Confirmed by grep:** no tool search, no embeddings, no semantic selection anywhere
  in `crates/agentgateway/src/mcp/`. It filters and authorises; it does not choose.

**Verdict:** the right thing to put *under* a router when you need infrastructure-grade
policy, mTLS and observability. Not a router. Same applies to **Docker MCP Gateway**,
whose `dynamic-tools` feature (`mcp-find`/`mcp-add`/`mcp-remove`) searches the *Docker
catalog for servers to install*, not your live tools for the right one — and which
auto-disables when you pin `--servers`.

---

### 10. Composio Tool Router / Rube — *the hosted option, with a serious asterisk*

Single MCP endpoint over 500+ integrations, session-scoped pre-signed MCP URLs, dynamic
tool discovery plus centralised OAuth. Operationally the least work: no index to run,
no upstream processes, no credential storage of your own.

- **The asterisk:** on **2026-05-21 Composio disclosed a breach** in which attackers
  exfiltrated approximately **5,241 API keys and 5,001 GitHub OAuth tokens**. The entry
  vector was a compromised employee Gmail OAuth token used to intercept magic-link
  sign-in emails and reach production secret stores; analyses describe a pivot through
  an internal agentic remediation system into the sandboxed execution environment,
  where attacker-registered tool definitions ran as trusted. All user GitHub tokens
  were revoked. This is from Composio's own disclosure, corroborated by multiple
  independent write-ups.
- **Independent efficiency criticism:** Arcade's published comparison measured 7,426
  tokens vs Composio's 747,083 across 8 CRM queries — a >100x gap attributed to
  Composio returning every field of every record with no field selection. Vendor-run
  benchmark, so discount it, but field selection is a real architectural difference.

**Verdict:** include it because it genuinely is the fastest path to "one endpoint,
hundreds of integrations". But a hosted router is a single point of compromise for
every credential you hand it, and this one has already been compromised once. If the
credentials matter, self-host options 2–4. Alternatives in the same slot:
**Klavis** (hosted Strata, benchmarked), **Arcade.dev** (field-selective, per-user
OAuth), **Smithery** (registry of ~2,500 unvetted community servers — discovery, not
production).

---

## Considered and not recommended

| Project | Why not |
|---|---|
| **MetaMCP** | Popular and genuinely useful, but 13 test files, 1 CI workflow, maintainer has publicly flagged maintenance delays, dev has moved to an `ai-dev` branch with AI-generated changes and a community fork exists. Static namespaces + middleware, no ranked selection. Fails "battle tested". |
| **MCPJungle** | Clean, well-documented Go gateway with tool *groups* — static curation only, no search. 0 CI workflow files in the clone. Fine as a team gateway, not a router. |
| **Hypertool MCP** | Manually/AI-curated toolsets. No commits since 2025-09-30. |
| **Director** | Nice "playbooks" model (static tool filtering), AGPL-3.0, but effectively single-author and last commit 2026-07-09. |
| **mcp-use** | Not a proxy — an agent library. Its `ToolSearchEngine` uses fastembed (`BAAI/bge-small-en-v1.5`) with in-memory brute-force cosine and a `ServerManager` that connects/disconnects servers. Excellent reference implementation if you build your own in Python; wrong shape if you want a layer in front of existing clients. |
| **AIRIS MCP Gateway** | 7 meta-tools with HOT/COLD server lifecycle, auto-enable on demand and circuit breaker; claimed 97% token reduction. Interesting design, thin track record. |
| **Lasso mcp-gateway** | Security plugin gateway, last commit 2026-01-22. Different problem. |

---

## What I would actually do

**If you are on Claude (you are):** you already have option 1 running. `ENABLE_TOOL_SEARCH`
is on by default, deferring MCP tool definitions and loading up to five per search, against
a ceiling of 10,000 tools. Do not build a second selection layer until you can show this one
failing — you would be replacing a server-side, prompt-cache-preserving mechanism with a
round-trip through your own index.

**Then add a proxy only for what tool search cannot do** — running, authenticating,
isolating and governing many MCP servers, and giving non-Claude clients the same
behaviour:

- Kubernetes / need hybrid semantic retrieval / need per-identity filtering → **ToolHive vMCP** (2)
- Local-first, one binary, security-conscious → **MCPProxy** (3)
- Retrieval accuracy is the dominant risk and you can run several services → **mcp-gateway-registry** (4)
- Already have an enterprise gateway mandate → **ContextForge** (8) or **agentgateway** (9) underneath, tool search on top

**The highest-leverage thing that is not on this list:** implement your own retrieval and
return `tool_reference` blocks from a custom tool. You keep Anthropic's context-window and
prompt-caching mechanics and own the ranking completely — embeddings, reranking, usage
priors, whatever your catalogue needs. That is the cheapest path to a router tuned to your
actual tools, and it composes with any of the proxies above.

**Whatever you choose, hold it to the bar the field mostly ignores:** a ground-truth query
set and an NDCG or pass@1 number in CI. MCPProxy and mcp-gateway-registry show what that
looks like. Without it you cannot tell a routing layer that is working from one that is
quietly picking the second-best tool.

---

## Sources

- [Tool search tool — Claude API](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)
- [Scale to many tools with tool search — Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/tool-search)
- [stacklok/toolhive](https://github.com/stacklok/toolhive) · [Virtual MCP Server docs](https://docs.stacklok.com/toolhive/concepts/vmcp)
- [smart-mcp-proxy/mcpproxy-go](https://github.com/smart-mcp-proxy/mcpproxy-go) · [docs.mcpproxy.app](https://docs.mcpproxy.app/)
- [agentic-community/mcp-gateway-registry](https://github.com/agentic-community/mcp-gateway-registry)
- [1mcp-app/agent](https://github.com/1mcp-app/agent)
- [Klavis-AI/klavis (open-strata)](https://github.com/Klavis-AI/klavis) · [Strata concepts](https://www.klavis.ai/docs/concepts/strata)
- [Nexus-Router/nexus](https://github.com/Nexus-Router/nexus) · [releases](https://github.com/Nexus-Router/nexus/releases)
- [IBM/mcp-context-forge](https://github.com/IBM/mcp-context-forge)
- [agentgateway/agentgateway](https://github.com/agentgateway/agentgateway)
- [docker/mcp-gateway](https://github.com/docker/mcp-gateway)
- [Composio Tool Router (beta)](https://composio.dev/blog/introducing-tool-router-(beta)) · [Composio May 2026 Security Incident](https://composio.ghost.io/composio-may-2026-security-incident/) · [Material Security analysis](https://material.security/resources/the-composio-breach-one-token-10242-doors)
- [Arcade vs Composio toolkit benchmark](https://www.arcade.dev/blog/attio-mcp-toolkit-benchmark/)
- [Progressive discovery vs semantic search (Speakeasy)](https://www.speakeasy.com/blog/100x-token-reduction-dynamic-toolsets/)
- [e2b-dev/awesome-mcp-gateways](https://github.com/e2b-dev/awesome-mcp-gateways)
