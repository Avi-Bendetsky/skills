# BAS-More/skills — Active Codex handover

**Status:** ACTIVE (routing benchmark finished 2026-09-29; the project-memory continuation remains, see "Session 2026-09-29")
**Updated:** 2026-10-06 (Australia/Melbourne)
**Default branch:** `main`
**Codex thread:** `codex://threads/01a03bc7-0d2a-75e2-8c3e-c9d125ded17e`
**Primary workstream:** semantic MCP/tool-routing benchmark and skills repository maintenance

## Evidence boundary

The Codex thread transcript is not available through this GitHub checkout or the connected repository API. This handover is reconstructed from the current repository, the retained benchmark handover under `docs/mcp-routing-benchmark/`, branches, commits, and PR history. Any thread-local change that was never committed is **not recovered** by this document.

## Executive state

> **2026-09-29:** the routing benchmark described below is **finished**. See
> "Session 2026-09-29" at the end of this file. The P0-P4 list is kept as the record
> of what was required.

The repository-level skill organization is established and governed by the existing project rules. The most important unfinished work is not ordinary skill curation: it is the routing evaluation documented in:

- `docs/mcp-routing-benchmark/HANDOVER.md`
- `docs/mcp-routing-benchmark/HANDOVER-PROMPT.md`
- `docs/mcp-tool-routing-layer-validation.md`

The research and lexical baselines were completed. The semantic benchmark was not completed because the cloud environment denied access to `huggingface.co`, which prevented the embedding model from being obtained. The retained handover records the measured conclusion that lexical routing does not scale to the real catalogue: on the 412-tool catalogue it reached roughly 21–23% top-1, and real descriptions did not remove that ceiling. The remaining question is whether a genuine semantic backend materially improves the result.

The repository also retains the branch `claude/mcp-tool-calling-layer-9g9q8j`. Do not assume its name means it is the current source of truth. Compare it by content against `main` before reusing or deleting it.

## Completed and preserved

- A real-catalogue routing study and lexical/control baselines exist.
- The benchmark documents record two scorer/harness defects that once produced near-zero results and were corrected:
  - missing workload-prefix normalization;
  - a parser that failed on newline-delimited JSON.
- The research records a critical diagnostic rule: when a gateway scores near zero, validate the scorer before blaming the gateway.
- A control path is specified: semantic BGE and non-semantic hash runs must be executed together so any gain is attributable to semantics rather than hybrid plumbing.
- Repository skill buckets and publication rules remain governed by `CLAUDE-PROJECT-RULES.md`.

## Unfinished work, in priority order

### P0 — recover the exact execution environment

1. From a clean clone, record:
   ```bash
   git status --short
   git branch --show-current
   git log --oneline -5
   git remote -v
   gh pr list --state open
   ```
2. Compare `claude/mcp-tool-calling-layer-9g9q8j` with `main` by content:
   ```bash
   git fetch --all --prune
   git diff --stat origin/main...origin/claude/mcp-tool-calling-layer-9g9q8j
   git log --left-right --cherry-pick --oneline origin/main...origin/claude/mcp-tool-calling-layer-9g9q8j
   ```
3. Preserve any unique work before branch cleanup. A merged PR status is not enough; verify files and commits.

### P1 — clear or accurately report the semantic-model blocker

The existing benchmark handover says the cloud egress proxy denied `huggingface.co`. At the start of a new session, test the blocker once using the documented bootstrap path. Do not repeatedly retry, tunnel around policy, change download hosts without review, or label a policy denial as a product failure.

If the denial remains, set this handover to `BLOCKED` and record the exact command, exit status, and denial message. The user must change the cloud environment policy in the UI; a running session cannot retroactively acquire that permission.

### P2 — run the semantic and control evaluations together

Once the embedding model is genuinely available, run from the benchmark directory using the retained commands:

```bash
THV=/tmp/thv EMBED_PYTHON=/tmp/embvenv/bin/python ./run-semantic.sh bge tokens
THV=/tmp/thv EMBED_PYTHON=/tmp/embvenv/bin/python ./run-semantic.sh hash tokens
```

For each run, record:

- backend and model;
- exact commit and configuration;
- top-1 and any other agreed metrics;
- empty-result rate;
- embedding request count;
- tool-surface overhead;
- errors and exclusions.

A semantic run with **zero embedding requests is invalid**, regardless of its score.

### P3 — interpret without tuning to the answer

Do not tune the query set, labels, catalogue, or `hybridSearchSemanticRatio` to make semantic search look better. Report disappointing numbers plainly. The decision is whether semantics beats the measured lexical ceiling under a fixed protocol, not whether the benchmark can be optimized after observing the result.

### P4 — close the research loop in the repository

Update `docs/mcp-tool-routing-layer-validation.md` with:

- the exact two-run comparison;
- whether semantic routing materially beats lexical;
- operational costs and failure modes;
- recommendation: ship, reject, or run a named follow-up;
- reproducible commands and environment details.

Then update the benchmark handover and this root handover. If no engineering work remains, change `Status:` to `COMPLETE`.

## Validation and repository rules

Before committing skill changes, verify the repository publication invariants:

```bash
./scripts/check-invariants.sh
```

It checks all of them mechanically, and the `Skill invariants` workflow runs it on
every pull request that touches `skills/`, `README.md`, the plugin manifest, or the
checker itself. The rules it enforces, unchanged from `CLAUDE-PROJECT-RULES.md`:

- every skill in `engineering/`, `productivity/`, or `misc/` is linked from the top-level `README.md`;
- every promoted skill appears in `.claude-plugin/plugin.json`;
- `personal/`, `in-progress/`, and `deprecated/` skills do not appear in those public indexes;
- each bucket README lists each skill with a link to its `SKILL.md`.

Reading the list by hand is no longer the check — it is the documentation of what the
check does. This list was a manual checklist up to 2026-10-06, and item 5 of the
routing benchmark's definition of done was missed under it (see "Session 2026-09-29").

Run the benchmark-specific checks documented beside the scripts. Do not use a generic green exit as proof that embeddings were exercised.

## Traps already paid for

- `pkill -f <pattern>` can kill the shell running it.
- A network policy change is normally read at session start; changing policy does not repair an already-running cloud session.
- Marketing claims are not implementation evidence.
- Counts alone are weak: two configurations can expose the same number of tools while exposing different server names.
- Do not commit model caches, tokens, credentials, virtual environments, or generated benchmark bulk unless the repository explicitly tracks them.

## Definition of done

This handover may be marked `COMPLETE` only when:

1. unique branch/thread work is either merged, intentionally archived, or explicitly declared unrecoverable;
2. the semantic backend ran and made non-zero embedding requests, or the owner formally closes the experiment without it;
3. semantic and hash controls were run under the same fixed protocol;
4. results and recommendation are committed to the validation document;
5. repository indexes and plugin manifest are consistent;
6. the final commit and PR are pushed and all required checks are green or their limitations are explicitly accepted.

## Handover maintenance

On every meaningful session stop, update this file and `HANDOVER-PROMPT.md` in the same commit. Keep the detailed benchmark handover for experiment-specific commands, but make this root file the single active status index.


## Independent project-memory templates — 2026-09-14

Avi separately requests the comprehensive MAH graph workflow across existing
repositories, with an offer for future projects. This independently requested
documentation work does not replace or complete the original ACTIVE semantic
routing benchmark.

Branch: `codex/project-memory-bootstrap-20260914`, based on skills commit `f980d479e904f3e2ee74db4534d7c291b00887db`.
Deliverables: `docs/project-memory/README.md`, `AGENTS.template.md` and
`GLOBAL.template.md` in that directory. They define an agent-readable bootstrap
policy, routine graph usage, nine-view coverage, privacy, acceptance criteria and
the user-level future-project offer.

Reference MAH: `688eee19709632f1a5fb6900184ff89217dddea1`; analyzer:
`557277c88feafbfd8b232ceacfda59d64b61ef81`.
The MAH implementation is project-specific. These templates do not supply a
generic executable installer, install tools on any computer, enroll repositories
or guarantee arbitrary agents comply. Source factoring, per-stack adapters,
pilot validation, individual target PRs and client configuration remain.

Read-only preparation used GitHub API equivalents for repository HEAD, tree and
open-PR inspection; no local Git worktree or project command was available because
the execution environment failed initialization. Reviewed the templates and
their source references; no runtime/installer/application test is claimed.
Existing skill buckets/public indexes and benchmark files are unchanged.

Continuation: read docs/project-memory/README.md and preserve the independent
ACTIVE workstream. Once an authorized execution host is available, implement and
validate the shared installer before representing this as automatic setup.
Keep the target repository's existing instructions, hooks and source data intact.


## Independent project-memory installation — 2026-09-14

This section supersedes the installation TODOs in the earlier template-preparation
section. It does not complete the original ACTIVE routing benchmark.

The owner authorized installation across existing repositories and active coding
clients. `scripts/project-memory/install.mjs` implements reversible policy setup,
identity/choice recording and instruction pointers while preserving original text,
frontmatter, line endings, hooks and supported instruction aliases. It is a policy
installer, not a universal nine-graph engine. See `docs/project-memory/INSTALL.md`.

The original eight tests passed on AVISURFACE; all nine tests passed in Linux and
Windows CI (run 34849931323). A later local repeat timed out; the final client
configuration was installed from the CI-verified source and hash-verified. Active
Codex override and Claude user rules include the future-project offer. No fresh
interactive agent session was used to prove behavioral compliance.

Each eligible target received an isolated PR with exact content/diff verification.
Normal merges proceed only with the verified head and clean checks; required
reviews, failing/pending checks and repository workflow constraints stay blockers.
See `docs/project-memory/rollouts/2026-09-14.json` for the aggregate snapshot.
Detailed repository inventories and client receipts are kept privately by the owner.
MAH's existing graph system is preserved. No project is marked graph-complete merely
because its policy files merged. The eight MAH external-service tests remain pending.

Privacy correction: the public PR initially contained repository-name and branch/status
metadata. HEAD contains aggregate counts only. Earlier public PR commits still retain
that metadata; removing the current inventory does not erase commit history. The
inventory did not contain credentials or source-file contents. Keep all detailed
portfolio records private and squash this PR when its normal merge gates pass.

Continuation: use the private rollout record to resolve open repository gates;
bootstrap and validate graphs per project under POLICY.md. Do not recreate verified
PRs or re-upload inventories. Maintain the separate benchmark handover unchanged.

Final installer validation: 11 tests pass on Linux and Windows in run 34859254533.
Three target formatter failures caused by the new memory files were corrected with
reviewed Markdown content, preserved existing instructions and source/block hash
receipts. Repository CI remains authoritative for their remaining gates. MAH's local
session freshness check passed with all nine views and fingerprint
`03424bdb1964993a731980ad3c6424c63de74112bb4adecee92148ffeb6a26e0`.


## Session 2026-09-29 — routing benchmark finished (Claude Code, branch `claude/go-bd9ae8`)

**P0-P4 of the routing benchmark are done.** The semantic run happened.

- **P0 (environment).** `main` was `83d2b74` at session start (now `27cf1e4`, after
  PR #12). `claude/mcp-tool-calling-layer-9g9q8j`
  no longer exists on the remote; its last PR head (#8, `9d77188`) is an ancestor of
  `main`, so nothing on it was lost. The Codex thread transcript remains unrecoverable
  and is declared so. The one unique commit found elsewhere, `eb3aa72` on
  `docs/drop-deprecated-qa-reference`, landed in `main` as `8e24f26` via PR #12.
- **P1 (blocker).** From the owner's PC, `huggingface.co` returned 307 → 200. The
  denial applied only to the Claude Code cloud environments. No mirror or substitute
  model was used.
- **P2 (runs).** The protocol was pre-registered and pushed before any score
  (`c378438`, `ab3199a`). All rows ran in a Linux container (`golang:1.24-bookworm`,
  Python 3.11.2, Go 1.26.0 via `GOTOOLCHAIN`) on the owner's remote Docker context
  `neko`, capped at 1.5 CPU / 1.2 GB because that host also runs staging services.
  ToolHive was pinned to `8343851e`. The model was `fastembed` 0.8.1 →
  `Qdrant/bge-small-en-v1.5-onnx-Q@aa8f8b06`.
- **Results.** The build reproduced both published baselines exactly (lexical
  21/44/49%, 1/43 empty; hash control 21/33/44%, 0/43). bge at the protocol ratio
  0.6 scored **44% top-1, 56% top-3, 60% top-5, 0/43 empty**, with 44 embedding
  requests. Repeats were identical. McNemar: vs hash control p = 0.006 (top-1 and
  top-3); vs pure lexical top-1 p = 0.021, top-3 p = 0.18. "change the schema
  safely" is still missed.
- **Finding.** ToolHive's hybrid search is semantic-first slot splitting, not score
  fusion (`hybridSearchLimits` / `mergeResults` in
  `pkg/vmcp/optimizer/internal/toolstore/sqlite_store.go`).
- **P3/P4.** The pre-registered verdict is "semantic materially beats lexical". It
  clears the 10-point bar against pure lexical by one query, and its significance
  test was met only against the non-semantic control. The recommendation is
  unchanged (the top-3 bar of 65% was not met). Written up as "Run 4" in
  `docs/mcp-tool-routing-layer-validation.md`. Per-row outputs, raw probe
  transcripts and `environment.txt` (build info, model hashes, container limits)
  are in `docs/mcp-routing-benchmark/results/run4/`.
- **Review.** An adversarial pass (4 independent reviewers: evidence, source
  mechanism, protocol compliance, statistics) raised 39 findings before commit. A
  second pass (2 reviewers) checked the fixes and raised 17 more, all low or
  medium. All were corrected or disclosed. The most serious was that the first
  draft had drifted from the pre-registered recommendation. Only per-row Wilson
  intervals are reported, not intervals on the paired differences; the write-up
  says so. The harness version line, which printed a banner, was fixed after the
  runs; the fix does not affect scoring.

Definition of done for the routing benchmark: items 1-6 are met.

- Item 5 was not met at first: `.claude-plugin/plugin.json` listed none of the four
  `skills/misc/` skills (`git-guardrails-claude-code`, `migrate-to-shoehorn`,
  `scaffold-exercises`, `setup-pre-commit`), although `CLAUDE-PROJECT-RULES.md`
  requires it. This predated the session. On the owner's decision (2026-09-29) the
  four entries were added on branch `claude/plugin-json-misc`, in README order.
- Item 6: the Run 4 PR #13 was merged by the owner on 2026-09-29 (merge `578950f`).
  Both Socket Security checks passed; CodeRabbit was still pending at merge.

Also this session: PR #12 (`project-memory-v2`: task-scoped project-memory wording
plus `eb3aa72`) was applied and tested here, then pushed, opened and merged by the
owner on 2026-09-29 (merge `27cf1e4`). Its installer tests passed 14/14 locally
before the push. The greyrok
transfer branch it came from is deleted.

Project memory: this repository has no `graph:*` commands or graph tooling, so the
graph steps were skipped. No graph was built or claimed.

State Git cannot show: the benchmark container `routing-bench-bd9ae8` and the two
images pulled for it (`golang:1.24-bookworm`, `alpine:3`) were removed from the
`neko` Docker host after the evidence was copied into `results/run4/`. Verified
with `docker ps -a` and `docker images`; the host's pre-existing `alpine:latest`
was left alone.

Remaining work, in order:

1. Owner review and merge of the `claude/plugin-json-misc` PR (the four `misc`
   entries in `plugin.json`).
2. The independent project-memory continuation above (per-project graph bootstrap
   and acceptance) is unchanged by this session.
3. Optional routing follow-ups (rank fusion, larger model, current ToolHive HEAD)
   are listed under "Status" in the validation doc. None is required.

## Session 2026-10-06 — publication invariants automated (Claude Code, branch `claude/repository-code-review-l65q2b`)

`main` was `0741c29` at session start and is unchanged by this session apart from this
branch. The previous session's remaining item 1 (merge of `claude/plugin-json-misc`)
is **done**: PR #14 landed as `fad207d`, so all four `skills/misc/` entries are in
`.claude-plugin/plugin.json`. Items 2 and 3 are untouched.

**What changed.** The publication invariants in `CLAUDE-PROJECT-RULES.md` were
convention-only — nothing checked them, and the only thing between an unpromoted
draft and the public plugin index was whoever remembered to edit three files at once.
They are now enforced:

- `scripts/check-invariants.sh` — six checks: every skill directory has a `SKILL.md`;
  every public skill has a manifest entry; every public skill is linked **by name**
  from `README.md`; no `personal/`/`in-progress/`/`deprecated/` skill appears in
  either public index; every bucket README lists each of its skills with a link and a
  one-line description; every manifest entry resolves to a real skill.
- `.github/workflows/skill-invariants.yml` — runs it on pull requests and pushes to
  `main` that touch `skills/**`, `README.md`, `.claude-plugin/plugin.json`, the
  checker, or the workflow. Those five paths are exactly the checker's inputs, so the
  path filter cannot skip a run that would change the outcome.

**Deliberately dependency-free** (bash + coreutils + grep; no node, no jq) so the
same command runs in CI, in a pre-commit hook, and on a laptop with nothing
installed. The manifest is a flat list of path strings, so a fixed-string grep reads
it correctly regardless of key order, and a skill name is never reinterpreted as a
regex.

**Verification.** `./scripts/check-invariants.sh` exits 0 on `0741c29`. Each of the
six checks was then confirmed to actually fire, against mutated copies in a scratch
directory (the repository was never dirtied):

| Mutation | Result |
| --- | --- |
| skill directory with no `SKILL.md` | fires (4 checks) |
| the four `misc/` entries removed from the manifest — replays the `fad207d` bug | fires, naming all four |
| README link target changed away from `SKILL.md` | fires |
| README link target correct but text does not name the skill | fires |
| private skill added to the manifest | fires |
| private skill referenced in `README.md` | fires |
| bucket README entry deleted | fires |
| bucket README entry left with no description | fires |
| bucket README "description" that is only an em-dash | fires |
| manifest entry pointing at a nonexistent skill | fires |

Two of those cases were found by this testing rather than by review: the description
check first passed a bare `**[name](./name/SKILL.md)**` line, because the house
format's trailing `**` satisfied a naive "any character after the link" test. It now
cuts the line at the link with a literal match and requires at least
`MIN_DESCRIPTION_CHARS` (10) of prose. A checker that only ever passes is worth
nothing, so the negative cases are the evidence, not the clean run.

`bash -n` is clean. `shellcheck` could **not** be run: this cloud session's egress
policy returned 403 for its binary download, so the script is behaviour-tested but
not statically linted — worth running once in an environment that has it.

**Not changed, deliberately.** The `Status:` field at the top of this file now holds
a prose sentence, while `00-READ-FIRST.md` defines it as the enum
`ACTIVE | BLOCKED | COMPLETE` and keys the mandatory session gate on it. A careless
or automated reader cannot parse the current value. Left alone because it changes
gate semantics and was outside what this session was asked to do; it is a one-line
fix for whoever owns that decision.

Remaining work, in order:

1. The independent project-memory continuation (per-project graph bootstrap and
   acceptance) is unchanged by this session.
2. Optional routing follow-ups (rank fusion, larger model, current ToolHive HEAD)
   are listed under "Status" in the validation doc. None is required.
3. Normalise the `Status:` field above to the documented enum, and run `shellcheck`
   over `scripts/check-invariants.sh` where the binary is available.
