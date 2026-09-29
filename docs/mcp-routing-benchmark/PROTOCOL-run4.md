# Run 4 protocol: semantic vs lexical routing (pre-registered)

Written and committed **before any Run 4 score was produced**, so the matrix,
validity gates and verdict thresholds below cannot have been chosen after seeing
the results. Results go in
[`../mcp-tool-routing-layer-validation.md`](../mcp-tool-routing-layer-validation.md)
as "Run 4: semantic". Deviations from this protocol are reported there, not
silently absorbed.

## Fixed for every row

| Item | Value |
|---|---|
| Router | ToolHive vMCP, built from `stacklok/toolhive@8343851e8a58086ff0768cd35856e14b11d273fd` |
| Why that commit | It was `main` HEAD from 2026-08-14 17:51Z until after the Run 2/3 baselines were published (PR #3, 2026-08-16 03:25Z). No commit in that window touches `pkg/vmcp/optimizer`, `pkg/vmcp/config`, `pkg/vmcp/server` or `cmd/vmcp`. |
| Catalogue | `real_catalogue.py`: 412 tools, 14 servers, 43 queries, unchanged |
| Harness | `run-semantic.sh` + `realbench.py` at the commit that adds this file |
| Optimizer | `maxToolsToReturn: 5`, `embeddingProvider: openai`, local `embedserver.py` |
| Model | `BAAI/bge-small-en-v1.5` as served by `fastembed` (version and artifact recorded with the results) |
| Host | Linux container (Debian 12, Python 3.11), capped at 1.5 CPU / 1200 MB on a shared host |

Latency is comparable **within Run 4 only**. The container is smaller than the
4-vCPU host of Runs 1-3, so absolute milliseconds are not comparable across runs.

## Matrix

| Row | Backend | Fixtures | Ratio | Role |
|---|---|---|---|---|
| R0 | hash | tokens | 0.0 | Build-parity check: must reproduce the published lexical baseline |
| **R1** | **bge** | **tokens** | **0.6** | **Primary semantic result** (run twice) |
| **R2** | **hash** | **tokens** | **0.6** | **Primary control** (run twice) |
| R3 | bge | real | 0.6 | Additional: semantic with real Supabase prose |
| R4 | hash | real | 0.6 | Additional: control for R3 |
| R5 | bge | tokens | 1.0 | Additional: embeddings alone, no lexical component |

0.6 is the protocol value. R0 and R5 are extra rows and never replace it.

## Validity gates

A row that fails a gate is reported as **invalid** with the reason, and not scored.

1. The `embedding backend:` line equals the requested backend.
2. `embedding requests during run` is greater than 0 for every row with ratio > 0.
3. `errors` is 0/43; otherwise the row is flagged and the errors are explained.
4. The catalogue line reads 412 tools across 14 servers.
5. `thv` was built from the commit above.
6. **Scorer check before any interpretation:** R0 must reproduce the published
   lexical baseline (top-1 21%, top-3 44%, top-5 49%, empty 1/43). If it does
   not, the harness is investigated first, and R1/R2 are interpreted only against
   R0 from the same build, never against the published figures. At least one raw
   `find_tool` response is also inspected by hand to confirm `names_in` parses it.

## Analysis

- **Primary comparison:** R1 vs R2. Same build, config and ratio; only the
  embedder differs, so any gap is attributable to semantics.
- **Secondary comparison:** R1 vs R0 (hybrid semantic vs pure lexical).
- **Primary metric:** top-3 (the model chooses from what comes back). Secondary:
  top-1, top-5, empty results, median latency, embedding requests.
- **Test:** exact two-sided McNemar (binomial on discordant queries), paired per
  query, on top-3 and on top-1. With n = 43, one query is 2.3 points.
- **Repeats:** R1 and R2 run twice. If a repeat differs, both are reported and
  the difference is treated as the noise band.

## Verdict rules

| Verdict | Condition |
|---|---|
| **Semantic materially beats lexical** | R1 top-3 is at least 10 points above **both** R0 and R2, **and** McNemar p < 0.05 for R1 vs R2 on top-3 |
| Directional improvement, not established | R1 top-3 above both R0 and R2, but the condition above fails |
| No improvement | R1 top-3 ≤ max(R0, R2) |

The current recommendation (Anthropic tool search for selection; ToolHive or
MCPProxy only for running, authenticating and isolating servers) changes only if
the verdict is "materially beats" **and** R1 clears the lexical ceiling by a wide
margin, defined here as top-1 ≥ 42% (≥ 18/43, double the ceiling) and top-3 ≥ 65%
(≥ 28/43). Even then, this benchmark cannot compare ToolHive against Anthropic's
server-side tool search, which is not testable from this harness.

## Not allowed

- Changing queries, labels, catalogue, fixtures, `maxToolsToReturn` or the 0.6
  ratio after seeing results.
- Substituting a different model or model host.
- Reporting a semantic score from a row with zero embedding requests.
