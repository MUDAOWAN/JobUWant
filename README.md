# JobUWant

JobUWant is a local web pilot tool for job-search information gathering and
role opportunity analysis.

The first MVP focuses on Hangzhou SLAM engineer / SLAM algorithm engineer
opportunities for campus hiring, including early hiring batches. It starts as a
personal localhost tool and may later become a public web application. The
current priority is product positioning and initial planning before technical
stack selection and business code.

## Current Status

- Project name: JobUWant
- Development environment: WSL2 Ubuntu
- Project path: `/home/votally/projects/JobUWant`
- Editor: VS Code
- Git branch: `main`
- Remote repository: `git@github.com:MUDAOWAN/JobUWant.git`
- Current phase: first MVP skeleton implementation

## First MVP Skeleton

The current code skeleton uses:

- Streamlit for the localhost UI.
- Python modules for the first simple harness.
- SQLite for local records.
- Local sample data only.

It does not call external search APIs or model APIs yet, so it does not consume
search quota, model tokens, or API budget.

Run command:

```bash
.venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Local URL:

```text
http://localhost:8501
```


## Public Repository Scope

This public repository contains the Streamlit pilot, the core Python analysis
modules, and the formal FastAPI + Next.js Web App under webapp/.

Local runtime data is intentionally not included:

- SQLite databases and generated JSON artifacts under data/
- local environment files and API credentials
- downloaded third-party project folders under download/
- local experiment helpers under i-param-flow-test/
- project-local toolchains, dependency folders, and build outputs

The current Web App UI and API layers are suitable for code review and local
development. Some live collection runner paths depend on local-only helper
files that are excluded from the public repository and should be formalized
before treating the public version as a complete runnable collection workflow.

## Planned Phases

1. Environment and project location setup
2. Documentation foundation
3. Product positioning and MVP scope
4. Product analysis and report structure design
5. Technical stack selection preparation
6. Agent workflow and project maintenance research
7. MVP development
8. Testing, iteration, and deployment planning
9. Launch and continued improvement

## Documentation Map

Core project documents live in `docs/`.

Read these first in a new Codex CLI session:

- `docs/CODEX_CLI_HANDOFF.md` - quick-start handoff for a new Codex CLI conversation.
- `docs/SESSION_HANDOFF.md` - current project state and next recommended steps.
- `docs/AGENT_RULES.md` - long-term collaboration and development rules.
- `docs/PROJECT_BRIEF.md` - project background, goal, and phase plan.

Project memory documents:

- `docs/DECISIONS.md` - important decisions and reasons.
- `docs/WORKLOG.md` - completed work, changed files, open items, and next steps.

Planned product and technical documents:

- `docs/PRODUCT_DESIGN.md` - product positioning, users, workflows, and MVP scope.
- `docs/TECH_ARCHITECTURE.md` - technical stack, architecture, and engineering decisions.
- `docs/ROADMAP.md` - phased roadmap from setup to launch.
- `docs/DATA_POLICY.md` - data source principles, quality rules, and cost controls.
- `docs/INFORMATION_INTAKE.md` - source discovery, job description location,
  confidence labels, and incremental update design.
- `docs/SKILL_RESEARCH.md` - Codex skill, harness, and agent workflow research notes.
- `docs/AGENT_PROCESS.md` - process record for agent collaboration,
  confirmed workflow rules, and execution notes.

## OpenAI Provider Setup

The app can keep using local sample data without any API key. To test the real
OpenAI web-search provider, create this file locally:

```text
.streamlit/secrets.toml
```

Add your key and optional model override:

```toml
OPENAI_API_KEY = "your_api_key_here"
OPENAI_BASE_URL = ""
OPENAI_MODEL = "gpt-5.5"
```

If you use an OpenAI-compatible relay, set `OPENAI_BASE_URL` to the relay base URL. If you use the official OpenAI API, keep it empty or remove it.

`secrets.toml` is ignored by Git and should stay local.

Install the OpenAI SDK before using the OpenAI provider:

```bash
.venv/bin/pip install -r requirements.txt
```

