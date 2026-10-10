# Install the approved memory policies

Run with Node.js 20 or newer from a checkout of this repository:

    node scripts/project-memory/install.mjs plan --root C:\path\to\repo --repository OWNER/REPO
    node scripts/project-memory/install.mjs install --root C:\path\to\repo --repository OWNER/REPO
    node scripts/project-memory/install.mjs status --root C:\path\to\repo

The installer copies the approved policy into .project-memory/POLICY.md,
records the repository identity and enabled choice in .project-memory/config.json,
and adds compact pointers to AGENTS.md and CLAUDE.md. Existing root
AGENTS.override.md and .claude/CLAUDE.md receive pointers too. Original text,
frontmatter and line endings remain intact outside the managed block. Existing
hooks, application manifests, MCP registrations and graph engines are preserved.

This installs instructions and records the setup choice. It is not standing
permission for agents to install tooling: the policy (v2) lets agents install graph
engines, hooks or CI checks only when the current task is project-memory setup or
the user confirms in the session, and tells them to skip graph steps where graph:*
commands or tooling are absent. It does not implement
MAH's project-specific graph extractors for every language or generate nine graphs.
Each project must finish the bootstrap and acceptance checks in POLICY.md before
its graph readiness is reported as complete. A PR proposes repository changes; the default branch changes only after that PR is merged.

For the active local coding clients:

    node scripts/project-memory/install.mjs clients
    node scripts/project-memory/install.mjs clients --apply

The client command appends opt-in project-memory guidance to Claude's user CLAUDE.md
and Codex's active AGENTS.override.md, or AGENTS.md when no override exists. The
rules follow an existing enabled setup, offer setup once to other projects, and ask
before installing anything; they do not enroll repositories on their own.
CODEX_HOME is honored; --profile and --codex-home allow explicit paths. Open a new
session so the client loads the changed instructions. These are model instructions,
not a background GitHub watcher or a mechanical proof of graph use. Other machines
and cloud clients require their own instruction configuration.

Each client is planned on its own, so one that cannot be installed does not stop the
other. A missing Codex home is reported as `skipped-client-home-missing` and is not
created, so a machine without Codex still gets Claude's rules; this holds for an
explicit `--codex-home` that does not exist as well. A client whose layout is refused,
such as a symlinked `~/.claude` from a dotfiles checkout, is reported as
`client-rules-unavailable` with the reason and the command exits 1; the other client
is still installed. The preview and apply reports name each client and its outcome.

A rerun with unchanged policy is a no-op. Edited policies, conflicting identities,
malformed blocks and unsafe symbolic links fail visibly. Root instruction aliases
between AGENTS.md, AGENTS.override.md and CLAUDE.md preserve their existing link
and update the regular target. Git's Windows symlink emulation is handled too. Deferred and declined choices
are preserved. The protected claude-home-backup repository is excluded.

Local changes have recovery journals. The command prints their exact locations:

    node scripts/project-memory/install.mjs rollback C:\path\to\journal.json

Rollback verifies current hashes and preserves concurrent edits. No broad
permission changes, dependency installation or Docker Desktop are required.

Validation:

    node --test scripts/project-memory/install.test.mjs

These tests cover policy installation and recovery. They do not count as graph
runtime acceptance or MAH external-service integration tests.

Keep detailed repository inventories private. The shared repository publishes only
aggregate rollout counts. Client rules (v2) no longer read a rollout registry or
treat it as approval.

## Upgrading from v1

Version 2 changes the managed block markers from `bas-more-project-memory:v1:*` to
`bas-more-project-memory:v2:*`, replaces the standing setup authorization with
task-scoped wording, and writes `schemaVersion: 2` and the new `policySha256` to
config.json. Rerun the installer per repository from an updated checkout:

    node scripts/project-memory/install.mjs plan --root C:\path\to\repo --repository OWNER/REPO
    node scripts/project-memory/install.mjs install --root C:\path\to\repo --repository OWNER/REPO

The v1 block is replaced in place (one block per file; surrounding text, frontmatter
and line endings are kept), the unedited v1 POLICY.md is replaced, and a second run
is a no-op. Commit the four files through that repository's normal PR process. A
repository whose v1 POLICY.md was edited, or that carries a `formatting` receipt,
fails visibly: review it, remove the stale receipt if appropriate, rerun, then
reformat and record a new receipt. Rerun `clients --apply` on each machine to
replace the v1 client rules; open a new client session afterwards.

Repository formatter compatibility:

After formatting the installed policy and managed instruction blocks, review the
formatted document content and confirm existing instructions outside the block are
unchanged. The installation record can retain that reviewed formatting with
`formatting.schemaVersion: 1`, the actual `tool` and `version`, the approved raw
`sourcePolicySha256`, and an `instructionBlockSha256` map keyed by instruction file.
Each block digest includes both managed markers. `policySha256` records the actual
formatted POLICY.md. These are integrity receipts for reviewed formatter output;
do not create them for an unreviewed policy rewrite. An upstream policy change or
edited formatted block fails visibly and requires a new review. Equivalent JSON
formatting is preserved. No formatter checks or repository gates are disabled.

The v1 installer passed 11 tests on Linux and Windows:
https://github.com/BAS-More/skills/actions/runs/34859254533
The v2 installer adds v1-to-v2 upgrade and marker tests (14 in total); CI for this
change runs through the project-memory-installer workflow on its PR.
