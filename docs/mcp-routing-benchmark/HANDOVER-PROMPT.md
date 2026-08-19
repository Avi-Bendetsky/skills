# Handover prompt

Paste everything below the line into a fresh Claude Code session on
`Avi-Bendetsky/skills`. It is self-contained.

---

You are picking up an MCP tool-routing evaluation. The research is finished and
merged; one measurement is outstanding. Read
`docs/mcp-routing-benchmark/HANDOVER.md` first — it has the full background.

## The question you are answering

On a 412-tool catalogue, every lexical retrieval engine tested lands at **21-23%
top-1**. The failures are semantic, not lexical: "change the schema safely" never
matches `apply_migration`, which is described as "Use this when executing DDL
operations". No keyword matcher bridges that.

**Does real semantic search beat the ~21% ceiling?** That is the whole task.

## Step 1 — check the blocker

The run needs `BAAI/bge-small-en-v1.5` from `huggingface.co`, which was blocked by
the cloud environment's network policy. Check first:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -m 15 \
  "https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/main/config.json"
```

**If that is not 200:** stop. Report it, include `curl -sS "$HTTPS_PROXY/__agentproxy/status"`,
and point at the fix in `HANDOVER.md` §4. **Do not route around it** — a 403 there is
an organisation policy denial, and the proxy's README requires reporting rather than
working around it. No mirrors, no alternate model hosts, no substituting a different
model to make the run "work". Note also that the policy is read at session start, so
if someone changes it while you are running, you need a brand-new session.

## Step 2 — prerequisites

```bash
git clone --depth 1 https://github.com/stacklok/toolhive /tmp/toolhive
(cd /tmp/toolhive && go build -o /tmp/thv ./cmd/thv)          # a few minutes
python3 -m venv /tmp/embvenv && /tmp/embvenv/bin/pip install fastembed
```

## Step 3 — run both conditions

```bash
cd docs/mcp-routing-benchmark
THV=/tmp/thv EMBED_PYTHON=/tmp/embvenv/bin/python ./run-semantic.sh bge  tokens
THV=/tmp/thv EMBED_PYTHON=/tmp/embvenv/bin/python ./run-semantic.sh hash tokens
```

Run **both**. `hash` is a deterministic hashed bag-of-words with no synonymy by
construction (`cos("refund a charge", "give the money back") = 0.0`). It is the
control: if hybrid-with-`hash` scores like plain lexical while hybrid-with-`bge`
scores much better, the gain is attributable to semantics rather than to the hybrid
plumbing. One number on its own proves little.

## Step 4 — report

For each run, quote verbatim:

- the `embedding backend:` line
- the score line (top-1 / top-3 / top-5 / empty-results / median)
- the `embedding requests during run:` line

**If embedding requests is 0, the semantic arm never ran and the result is
meaningless — say so rather than reporting the score.**

Compare against these, already measured on the identical catalogue:

| Condition | top-1 | top-3 | top-5 | empty | median |
|---|---|---|---|---|---|
| ToolHive lexical only (FTS5, ratio 0) | 21% | 44% | 49% | 1/43 | 3 ms |
| ToolHive hybrid, non-semantic control | 21% | 33% | 44% | 0/43 | 48 ms |

## Step 5 — write it up

Add the results to `docs/mcp-tool-routing-layer-validation.md` as "Run 4: semantic",
following the style of the existing runs: state the method, the numbers, what
changed, and what it means for the recommendation. Update the "What is still needed
to finish this" section, since it will no longer be outstanding.

Then update the verdict if the numbers justify it. The current recommendation is:
keep Anthropic's tool search doing selection, and add ToolHive or MCPProxy only for
running, authenticating and isolating servers. If semantic search clears the ceiling
by a wide margin, a self-hosted router becomes worth its operational cost and that
recommendation should change. If it does not, say so plainly.

Commit and push to `claude/mcp-tool-calling-layer-9g9q8j` and open a draft PR.

## Rules

- **Report disappointing numbers plainly.** Do not tune the query set, the config,
  `hybridSearchSemanticRatio` or `maxToolsToReturn` to improve the result. If you
  want to test a different ratio, report it as an *additional* row, never as a
  replacement for the 0.6 default.
- **Do not trust a near-zero score without checking the scorer.** Two false results
  were caught this way already: vMCP scored 0% until `realbench.py::names_in` was
  taught to strip its `{workload}_` prefix, and Nexus scored 2% until the parser
  handled newline-delimited JSON. If a gateway scores near zero, suspect the harness
  first.
- **Do not commit run artifacts.** `.work/` and `__pycache__/` are gitignored; keep
  it that way.
- **Do not use `pkill -f <pattern>`** for teardown — it matches the shell running it
  and kills your own command. `run-semantic.sh` cleans up after itself.
