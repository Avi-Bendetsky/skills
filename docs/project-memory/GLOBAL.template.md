# Offer comprehensive memory for new projects

Append this policy to the coding client's existing user-level instruction file.
This document is a template; saving it in this repository does not configure a
computer or register a ChatGPT skill.

## Policy to append

At the first coding session for a project, inspect its existing project-memory
setup and recorded choice. If neither exists, offer once:

"Would you like the comprehensive project-memory setup used in MAH, adapted to
this project, with local semantic memory and graph freshness checks?"

Ask before installing anything, unless the current task is project-memory setup
for this repository. Record the owner's choice as enabled, deferred or declined
in the project setup notes. Do not repeatedly offer after a recorded decision.

For enabled projects, follow the repository's agent instructions, current
handover and documented graph session/context/impact/change-detection workflow.
Use graph commands only where they are already set up; if the repository's
graph:* commands or tooling are absent, skip those steps rather than building
them. Install setup only after the confirmation above, then record actual
installation/validation results. A template is not an installed graph system.

Preserve existing user/project instructions. Do not index other repositories,
upload private source, change machine-wide permissions or rewrite handovers as
part of routine onboarding.

## Client locations

- Codex CLI/compatible local environments: the active Codex home `AGENTS.md`,
  normally `~/.codex/AGENTS.md`. An existing `AGENTS.override.md` can supersede it.
- Claude Code: `~/.claude/CLAUDE.md`.
- Other coding clients: their documented user-level rules/settings. Verify the
  rule loads in that client; do not assume every client reads AGENTS.md.
- ChatGPT Work/cloud: the policy must be available in that environment through
  supported instructions or an installed skill/plugin. A file on AVISURFACE does
  not automatically configure every cloud session or another computer.

These defaults apply when an agent starts work in a project; they do not monitor
GitHub for new repositories in the background. Unattended discovery would require
a separately implemented and authorized service.

References:
- https://learn.chatgpt.com/docs/agent-configuration/agents-md
- https://code.claude.com/docs/en/memory
