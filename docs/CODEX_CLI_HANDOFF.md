# Codex CLI Handoff

This is the first file a new Codex CLI conversation should read.

## Project Summary

JobUWant is a job-search information gathering and role analysis project. The
user enters a role name, and the future tool should produce structured findings
such as compensation level, city differences, education and experience
requirements, skill requirements, skill priority, job-search suggestions,
learning paths, and resume improvement directions.

The project starts as a personal-use tool. A public web application may come
later, but product positioning, data principles, technical direction, and cost
control must be clarified before business code starts.

## Current State

- Project name: JobUWant
- Current phase: first MVP skeleton implementation
- Formal WSL path: `/home/votally/projects/JobUWant`
- Windows UNC path: `\\wsl.localhost\Ubuntu\home\votally\projects\JobUWant`
- Git branch: `main`
- GitHub remote: `git@github.com:MUDAOWAN/JobUWant.git`
- Streamlit local MVP skeleton exists.
- Current skeleton uses Python, Streamlit, SQLite, a simple in-repo harness, and
  local sample data.
- It does not call external search or model APIs yet.
- Documentation and skeleton code have not been committed yet unless Git history
  says so.

## How To Open This Project

From Windows Codex CLI, use the UNC path as the working directory:

```powershell
codex -C "\\wsl.localhost\Ubuntu\home\votally\projects\JobUWant"
```

Inside WSL or VS Code Remote WSL, use the Linux path:

```bash
cd /home/votally/projects/JobUWant
```

## Command Preference

The project lives in WSL. Prefer WSL execution for project commands:

```powershell
wsl -e git -C /home/votally/projects/JobUWant status --short --branch
```

Use Windows paths only when the Windows Codex CLI needs to read or edit files.

## Read Order

Read these files before making changes:

1. `docs/CODEX_CLI_HANDOFF.md`
2. `docs/SESSION_HANDOFF.md`
3. `docs/AGENT_RULES.md`
4. `docs/PROJECT_BRIEF.md`
5. `docs/DECISIONS.md`
6. `docs/WORKLOG.md`

Use these documents later when their phase starts:

- `docs/PRODUCT_DESIGN.md`
- `docs/TECH_ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/DATA_POLICY.md`
- `docs/SKILL_RESEARCH.md`

## Collaboration Rules

- Do not start business code before product positioning and technical analysis.
- Do not install dependencies without explicit user approval.
- Do not push to GitHub without explicit user approval.
- Explain important file, Git, or environment changes before making them.
- Record important decisions in `docs/DECISIONS.md`.
- Record completed work and next steps in `docs/WORKLOG.md`.
- Keep `docs/SESSION_HANDOFF.md` current when the conversation grows long.

## Current Run Command

`ash
.venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
`

Local URL:

`	ext
http://localhost:8501
`

## Next Recommended Work

1. Review the current documentation.
2. Run and test the current local sample-data MVP skeleton.
3. Decide whether to test OpenAI web search or Tavily first for source
   discovery.
4. Verify the exact model identifier and availability before implementation.
5. Implement real source discovery providers after API choices and credentials
   are confirmed.
6. Make the first Git commit after the user confirms the MVP skeleton runs well
   enough to preserve as a baseline.

## Starter Prompt For A New Codex CLI Conversation

Use this prompt in a new Codex CLI session:

```text
You are working on JobUWant. The project is located at:
\\wsl.localhost\Ubuntu\home\votally\projects\JobUWant

First read these files in order:
1. docs/CODEX_CLI_HANDOFF.md
2. docs/SESSION_HANDOFF.md
3. docs/AGENT_RULES.md
4. docs/PROJECT_BRIEF.md
5. docs/DECISIONS.md
6. docs/WORKLOG.md

After reading them, summarize:
- the current project state
- the active phase
- the next recommended step
- any decisions that require my approval

Do not install dependencies, push to GitHub, or make major technical decisions
unless I explicitly approve.
```

