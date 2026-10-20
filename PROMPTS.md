# PROMPTS.md

## Project setup and M1 � October 2026

### Project planning
- Reviewed the official internship instructions and Problem 4 specification.
- Planned implementation milestones, business rules, testing, deployment, and submission documentation.

### M0 � Scaffold
- Set up the project structure, Python backend configuration, environment examples, and Git ignore rules.

### M1 � Data model and persistence
- Defined SQLAlchemy models for farmers, crops, crop grades, price-list entries, advances, deliveries, and payouts.
- Created and applied the initial Alembic migration.
- Created an idempotent seed script using illustrative sample data.
- Documented business-rule test cases for pricing, moisture deductions, rounding, payouts, advances, and correction notes.

### Testing and review
- Checked Python syntax and Ruff formatting/linting for the seed script and business-rule specification.
- Confirmed that the business-rule test cases are currently specification placeholders; they must be implemented as executable tests in M2.
- Avoided running the seed script against the configured Neon database.

## M2 - Business rules (Claude Code)

| # | Tool | Prompt | What I did with it |
|---|------|--------|--------------------|
| 1 | Claude Code | "Read and thoroughly understand the code till now and the 2 documents (common instructions + Problem 4); I did M0 and M1, continue with the remaining milestones, one at a time." | Used. Reviewed the repo, then generated pure domain modules (errors, clock, delivery rules, payout rules, note rules) and unit tests for M2. Ruff config fixed; placeholder spec tests replaced by executable tests. |

## M3 - API (Claude Code)

| # | Tool | Prompt | What I did with it |
|---|------|--------|--------------------|
| 2 | Claude Code | "Is it necessary to use SQLite? Tables are set in Neon (no data). Neon is the hosted DB. Yes, React + TypeScript + Vite for FE." | Used the answer: tests and local dev run on a Docker PostgreSQL, Neon is hosted only. |
| 3 | Claude Code | "I started Docker Desktop. Go." | Used. Generated services, FastAPI routers, error mapping, logging and API tests; I reviewed the concurrency design (per-farmer row lock) and edge-case tests. Fixed two bugs the tests exposed (mapper join for crop, log-record key collision). |

## M3 follow-ups and M4 - UI (Claude Code)

| # | Tool | Prompt | What I did with it |
|---|------|--------|--------------------|
| 4 | Claude Code | "Is the M3 completely done?" | Used the honest gap list (ledger unbounded, no coverage report). |
| 5 | Claude Code | "Close the ledger pagination gap and commit the coverage report before starting M4." | Used. Ledger capped with counts, advances list added, `scripts/coverage_report.py` writes coverage.txt. |
| 6 | Claude Code | "go" (start M4) | Used. Generated the React + TypeScript + Vite screens, API client and unit tests; I checked every flow in headless Chromium (21 checks, including 375px width) and fixed layout nits it showed. |

## M5 - Deployment (Claude Code)

| # | Tool | Prompt | What I did with it |
|---|------|--------|--------------------|
| 7 | Claude Code | "Don't start M5, got an issue on hitting /payouts" (pasted backend log) | Used the diagnosis: Neon lacked the new migration; I ran `alembic upgrade head` myself on the command it gave me. |
| 8 | Claude Code | "Go, first tell me what all things to be done for M5" | Used the plan and split between repo work and manual dashboard steps. |
| 9 | Claude Code | "Decisions: Render+Vercel+Neon yes; seed: do the best option; richer seed yes; repo name kjbn-hackathon" | Used. Seed Neon from the Render deploy, not from my machine. Generated Dockerfiles, compose, render.yaml, vercel.json, CI, seed; I verified the compose stack in a browser and validated render.yaml against Render's JSON schema. |

## Important implementation constraint
The official internship documents are the source of truth for requirements. Any assumptions must be identified explicitly, and implementation decisions must not silently introduce unsupported business rules.
