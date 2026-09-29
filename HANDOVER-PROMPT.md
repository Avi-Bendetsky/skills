# Continuation prompt — BAS-More/skills

> **Update 2026-09-29: the routing-benchmark objective below is complete** (Run 4 in
> `docs/mcp-tool-routing-layer-validation.md`; summary in `HANDOVER.md` → "Session
> 2026-09-29"). Do not re-run it. What remains:
> 1. Get the owner's decision on the `.claude-plugin/plugin.json` gap: the four
>    `skills/misc/` skills are missing.
> 2. Owner review and merge of the Run 4 PR. PR #12 (project-memory v2) is already
>    merged.
> 3. The project-memory continuation sections at the end of this prompt.

You are continuing Codex thread `01a03bc7-0d2a-75e2-8c3e-c9d125ded17e` in `https://github.com/BAS-More/skills`.

Before doing anything:

1. Read `00-READ-FIRST.md`, `HANDOVER.md`, `AGENTS-PROJECT-RULES.md` if present, and `CLAUDE-PROJECT-RULES.md`.
2. Read `docs/mcp-routing-benchmark/HANDOVER.md`, its prompt, and `docs/mcp-tool-routing-layer-validation.md`.
3. Run `git status --short`, `git branch --show-current`, `git log --oneline -5`, `git remote -v`, and `gh pr list --state open`.
4. Compare `origin/main` with `origin/claude/mcp-tool-calling-layer-9g9q8j` by content. Preserve unique commits before cleanup.
5. Do not assume the private Codex transcript is available or that uncommitted thread work exists on GitHub.

Primary objective: finish the semantic MCP/tool-routing evaluation without tuning the benchmark to the desired outcome.

- Check the documented `huggingface.co` blocker once.
- If policy still denies access, record exact evidence, set the handover to `BLOCKED`, and stop rather than working around policy.
- When clear, run both BGE semantic and hash control commands under the same configuration.
- Reject any semantic result with zero embedding requests.
- Record top-1, empty-result rate, embedding calls, overhead, exclusions, commit, and configuration.
- Update `docs/mcp-tool-routing-layer-validation.md` with a reproducible conclusion.
- Maintain the skill bucket, README, and plugin-manifest invariants.

Do not kill processes with broad `pkill -f`, commit caches/secrets, or report a score before validating the scorer.

Before stopping, update `HANDOVER.md` and this prompt, run the relevant checks, commit, push, and open/merge a PR according to repository protections. Mark the handover `COMPLETE` only when its definition of done is fully evidenced.


## Independent project-memory template continuation — 2026-09-14

Avi also requests comprehensive MAH-style memory graphs across repositories and
an offer for future projects. The separate branch `codex/project-memory-bootstrap-20260914`
adds docs/project-memory/README.md plus project/global instruction templates.
Read those files and the matching HANDOVER.md section when continuing this task.
They are bootstrap instructions, not a verified universal installer. Factor and
test the shared toolkit, adapt extractors per repository, then perform the
authorized rollout and configure the actual clients. Preserve the original
ACTIVE routing benchmark and do not claim it or MAH's external-service tests
were completed by this documentation work.


## Project-memory installation continuation — 2026-09-14

The approved templates now have a tested policy installer; start with
`docs/project-memory/INSTALL.md`, then the latest installation section in HANDOVER.md.
Codex and Claude user instructions were installed and hash-verified on AVISURFACE.
The repository rollout has isolated, verified PRs and merges subject to normal gates.
Read the aggregate snapshot and the owner's private detailed record before doing
further work; do not repeat already verified installation or publish private inventory.

The next substantive memory task is per-project graph bootstrap and acceptance,
plus resolving the recorded repository gates. Policy installation is not proof of
nine-graph readiness or actual agent compliance. Preserve the existing MAH setup,
the separate eight pending external-service cases and the original ACTIVE benchmark.
Earlier public PR history contains portfolio metadata; HEAD is aggregate-only.

The final installer has 11 passing Linux/Windows tests, including formatter receipts.
MAH's nine-view session freshness check passed. Use the private final record for
per-repository merge outcomes; the public JSON records scope only.
