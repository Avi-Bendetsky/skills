# Reusable comprehensive project-memory policy

The approved templates now have a tested policy installer. Follow [INSTALL.md](INSTALL.md)
to install repository instructions and configure the Codex and Claude user rules.
Installation records an enabled setup choice; each project still needs its graph
bootstrap and acceptance checks before graph readiness is complete.

The current policy is version 2 (`bas-more-project-memory:v2` markers). It does not
grant standing setup authorization: agents install graph engines, hooks or CI checks
only when the current task is project-memory setup or the user confirms in the
session, use the workflow only where it is already set up, and skip graph steps
where a repository has no graph:* commands or tooling. The client rules are opt-in
guidance that ask before installing. To roll v2 out, rerun the installer per
repository and `clients --apply` per machine; see
[INSTALL.md](INSTALL.md#upgrading-from-v1).

## Files to use

- [INSTALL.md](INSTALL.md): plan, install, status, client configuration and recovery commands.
- [AGENTS.template.md](AGENTS.template.md): approved per-project bootstrap, routine memory use,
  nine-view coverage, privacy and acceptance policy. The installer preserves it in
  `.project-memory/POLICY.md` and inserts compact pointers into existing instructions.
- [GLOBAL.template.md](GLOBAL.template.md): the future-project offer template.
  Use the installer client command to select the actual active Codex/Claude file.
- [rollouts/2026-09-14.json](rollouts/2026-09-14.json): aggregate v1 rollout snapshot.
  Detailed repository inventories are kept privately.

A repository file is read by clients that support that instruction mechanism; it
is not a background watcher or proof that every arbitrary agent followed it.
Open a new client session after changing global rules. Other machines and clients
need their own supported instruction configuration.

## Reference implementation

MAH is pinned at `688eee19709632f1a5fb6900184ff89217dddea1`, with analyzer
`557277c88feafbfd8b232ceacfda59d64b61ef81`. See its
[setup guide](https://github.com/BAS-More/MAH/blob/688eee19709632f1a5fb6900184ff89217dddea1/docs/agent-context/setup.md).
It supplies structural, dependency, compiler-module, database, process, hierarchy,
semantic, contract and workflow views, with freshness and context/impact commands.
Its extractors are project-specific. Reusing its generated graphs in a different
repository would misrepresent that project's source.

## Remaining graph work

For each enabled repository, identify applicable source languages, databases and
existing graph tooling. Adapt pinned extractors; preserve source and local privacy.
Validate all applicable views, real local semantic retrieval, source fingerprints,
stale/partial-stage rejection and checkout isolation. Record unsupported scopes
separately from genuinely inapplicable ones, with evidence. Finish POLICY.md's
acceptance criteria before changing graph readiness to complete.

The current installer deploys policy and setup choices. It does not implement a
universal graph runner, register every editor MCP server, or generate nine graphs.
Keep tooling pinned and review upgrades; preserve existing hooks and protection gates.

## Validation and rollout evidence

- The original eight installer preservation/recovery tests passed on AVISURFACE.
- All eleven tests, including Windows Git instruction links and reviewed formatting, passed on
  Linux and Windows CI: [verified run](https://github.com/BAS-More/skills/actions/runs/34859254533).
- A later local repeat timed out; no pass is claimed for that attempt.
- Version 2: 14 installer tests (including v1-to-v2 repository and client-rule
  upgrades) passed locally on Linux with Node 22; this repository's own files were
  upgraded by rerunning the installer, and a second run reported no changes.
- Codex's active override and Claude's user instruction file were written and
  hash-verified on AVISURFACE. A fresh interactive agent session was not exercised.
- Repository changes are read back exactly and compared with their planned file set;
  merged changes are read back from the default branch. Failed/pending checks and
  repository workflow requirements remain recorded blockers.
- The original semantic-routing benchmark remains a separate ACTIVE workstream.
  MAH's eight pending external-service cases were not run by these installer tests.

No broad ACL traversal, Docker Desktop installation or source upload to an external
embedding service is required by this policy deployment.
