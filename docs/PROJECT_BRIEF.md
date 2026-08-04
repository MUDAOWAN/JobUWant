# Project Brief

## Project Name

JobUWant

## Goal

Build a job-search information gathering and role opportunity analysis tool.
The user enters or selects a target role, city, hiring season, candidate status,
and optional direction. The tool will organize public job information, company
information, hiring requirements, and technical capability requirements into a
structured and visual report.

The long-term product may support general roles and cities. The first MVP is
intentionally narrow: Hangzhou SLAM engineer / SLAM algorithm engineer
opportunities for campus hiring, including early hiring batches.

## Initial Positioning

The first stage is a personal localhost web pilot tool. A public web
application is possible later, but the project should first validate the
product structure, report usefulness, data strategy, technical approach, and
cost profile.

## First MVP Scope

- City: Hangzhou
- Role: SLAM engineer / SLAM algorithm engineer
- Hiring stage: campus autumn hiring, compatible with early hiring batches
- Target user: the project owner
- Product shape: localhost web pilot tool
- Account system: not needed in the first version
- Data storage: undecided; compare local database and future cloud database
  options during technical stack selection

## First MVP Priorities

1. Technical stack and capability analysis.
2. Company-category requirement comparison.
3. Hangzhou company opportunity map.
4. Campus-hiring capability summary for new graduates.
5. Cost and token usage visibility for each query.

## Confirmed Setup

- Development system: WSL2 Ubuntu
- Project path: `/home/votally/projects/JobUWant`
- Editor: VS Code
- Git: enabled
- GitHub remote: `git@github.com:MUDAOWAN/JobUWant.git`
- Current Codex CLI access pattern: Windows Codex CLI can work with the WSL
  project through the UNC path `\\wsl.localhost\Ubuntu\home\votally\projects\JobUWant`.

## Phase Plan

1. Confirm local development environment and project location.
2. Create documentation foundation and collaboration rules.
3. Define product positioning and MVP scope.
4. Design the analysis report structure and data fields.
5. Prepare technical stack selection based on the product design.
6. Research agent workflow support and long-term project maintenance.
7. Build and test the MVP in small iterations.
8. Prepare deployment and cost planning.
9. Launch and continue improving the product.

## Documentation Roles

- `README.md`: project entry point and document map.
- `docs/CODEX_CLI_HANDOFF.md`: quick-start guide for new Codex CLI sessions.
- `docs/SESSION_HANDOFF.md`: current state and handoff notes.
- `docs/AGENT_RULES.md`: collaboration and development rules.
- `docs/DECISIONS.md`: decision history.
- `docs/WORKLOG.md`: work history and next steps.
- `docs/PRODUCT_DESIGN.md`: product analysis and MVP scope.
- `docs/TECH_ARCHITECTURE.md`: technical architecture once product scope is clearer.
- `docs/ROADMAP.md`: phased plan and milestones.
- `docs/DATA_POLICY.md`: data source, quality, and cost principles.
- `docs/SKILL_RESEARCH.md`: Codex skill, harness, and agent workflow research.
