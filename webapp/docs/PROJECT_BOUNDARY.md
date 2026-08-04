# Web App Project Boundary

Status: active boundary for the formal Web App work.

## Purpose

All formal Web App code should live under the webapp directory.

This keeps the new product surface separate from:

- the Streamlit pilot in app.py
- the existing jobuwant Python analysis modules
- the existing data artifacts under data
- the BOSS-related experiment and collection scripts under ai-param-flow-test and download

## Current Decision

Use FastAPI plus Next.js plus SQLite first.

- FastAPI owns API contracts, task state, and service wrapping.
- Next.js owns the public-ready frontend, local application shell, report pages, and future public pages.
- SQLite remains the first local database.
- Existing Python modules remain the source of validated analysis behavior.

## Next Work Gate

Before building full pages, define the backend API contracts and task-level state tables.

The next practical step is backend fixture-first design:

- task list and task detail contracts
- fixture binding for search_run_id 7 and search_run_id 8
- report input read endpoint
- final report read endpoint
- job sample table endpoint

## Skill Usage

Do not install skills yet.

Use skills by phase:

- design phase: ui-ux-pro-max or frontend-design
- Next.js implementation phase: vercel-react-best-practices
- UI review phase: web-design-guidelines or frontend-design-review
- browser verification phase: webapp-testing

