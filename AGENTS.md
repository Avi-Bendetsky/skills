<!-- bas-more-project-memory:v2:start -->
## Project memory
After the repository's mandatory entry and handover reads, read
.project-memory/config.json and .project-memory/POLICY.md from the repository root.
Use the graph workflow only where it is already set up. If graph:* commands or
graph tooling are absent, skip the graph steps (do not build them) and say so in
the handoff. Install graph engines, hooks or CI checks only when the current task
is project-memory setup or the user confirms in this session. Preserve any
working graph engine and its recorded pins.
Where set up, use the documented session/freshness, context and upstream-impact
workflow before coding; after edits, refresh relevant graphs and record actual
validation. Graph readiness requires the policy's acceptance evidence; installed
rules alone do not establish that graphs, semantic retrieval, hooks or
integrations work.
<!-- bas-more-project-memory:v2:end -->

# Mandatory session entry point

Before inspecting code, running commands, or changing Git state, read these files in order:

1. [`00-READ-FIRST.md`](00-READ-FIRST.md)
2. [`HANDOVER-PROMPT.md`](HANDOVER-PROMPT.md)
3. [`HANDOVER.md`](HANDOVER.md)
4. [`AGENTS-PROJECT-RULES.md`](AGENTS-PROJECT-RULES.md), when present

The handover gate remains mandatory while `HANDOVER.md` says `Status: ACTIVE` or `Status: BLOCKED`.
A newer handover supersedes it only when the pointers above are updated in the same commit.

After the handover, follow the preserved project rules in `AGENTS-PROJECT-RULES.md`.
