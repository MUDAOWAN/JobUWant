# Agent Rules

These rules guide long-term collaboration on JobUWant.

## Collaboration Rules

- Ask before making important project decisions.
- Explain planned file or environment changes before making them.
- Do not delete unknown files, code, or configuration.
- Keep changes scoped to the current task.
- Update project documents after meaningful phase-level work.
- Maintain a session handoff document when the conversation becomes long.
- Record technical decisions in `docs/DECISIONS.md`.
- Record completed work and next steps in `docs/WORKLOG.md`.

## Development Flow

1. Clarify the current phase.
2. Confirm decisions that affect project direction.
3. Make small, focused changes.
4. Verify the result.
5. Record what changed.
6. Suggest the next step.

## Codex CLI Working Rules

- New Codex CLI sessions should first read `docs/CODEX_CLI_HANDOFF.md`.
- The formal project path inside WSL is `/home/votally/projects/JobUWant`.
- Windows tools can access the project through
  `\\wsl.localhost\Ubuntu\home\votally\projects\JobUWant`.
- When running project commands from Windows Codex CLI, prefer WSL execution for
  project-related Git, Python, Node.js, service, and test commands.
- Do not install dependencies, push to GitHub, or start business code without
  explicit user approval.

## Current Priority

The current priority is documentation foundation and product positioning. Business
code should wait until product scope and technical direction are clearer.
