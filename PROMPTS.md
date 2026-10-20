# PROMPTS.md

## Project setup and M1 - October 2026

### Project planning
- Reviewed the official internship instructions and Problem 4 specification.
- Planned implementation milestones, business rules, testing, deployment, and submission documentation.

### M0 - Scaffold
- Set up the project structure, Python backend configuration, environment examples, and Git ignore rules.

### M1 - Data model and persistence
- Defined SQLAlchemy models for farmers, crops, crop grades, price-list entries, advances, deliveries, and payouts.
- Created and applied the initial Alembic migration.
- Created an idempotent seed script using illustrative sample data.
- Documented business-rule test cases for pricing, moisture deductions, rounding, payouts, advances, and correction notes.

### Testing and review
- Checked Python syntax and Ruff formatting/linting for the seed script and business-rule specification.
- Confirmed that the business-rule test cases are currently specification placeholders; they must be implemented as executable tests in M2.
- Avoided running the seed script against the configured Neon database.

## Claude Code (M2 onward)

Every message I typed to Claude Code, in order and verbatim. The first message came with the two
assignment PDFs attached (common instructions and Problem 4). Claude Code also produced the
generated code described in the last column; I reviewed and ran it.

| # | Tool | Prompt (verbatim) | What I did with it |
|---|------|-------------------|--------------------|
| 1 | Claude Code | "Read and thoroughly understand the code till now...the 2 documents are given...read and thoroughly understand them also / if u have any dount ask me / i did milestones M0 and M1...lets continue do the remaining / lets go milestone by milestone" | Used. It reviewed the repo and PDFs, fixed the ruff config, and generated the M2 domain modules and executable tests that replaced my placeholder specs. |
| 2 | Claude Code | "is it necessary to use SQLite...tables are well set in neondb(but no data) / neon is the hosted db / yes, React + TypeScript + Vite for FE" | Used the answer: tests and local development run on a Docker PostgreSQL; Neon is used only for the hosted instance. |
| 3 | Claude Code | "i started docker desktop / go" | Used. It generated the M3 services, routers, error mapping, logging and API tests. I reviewed the per-farmer locking design and the edge-case tests. Two bugs its tests exposed were fixed (crop join mapping, log-record key collision). |
| 4 | Claude Code | "is the M3 completely done?" | Used its list of remaining gaps (unbounded ledger lists, no coverage report). |
| 5 | Claude Code | "close the ledger pagination gap and commit the coverage report before starting M4" | Used. Ledger lists are capped with counts, an advances list endpoint was added, and `scripts/coverage_report.py` writes `backend/coverage.txt`. |
| 6 | Claude Code | "go" | Used. It generated the React + TypeScript + Vite UI, API client and unit tests; its headless-browser run (21 checks incl. 375px width) led to layout fixes. |
| 7 | Claude Code | "dont start M5...got an issue on hitting http://localhost:5173/payouts" plus the pasted uvicorn error log (a missing `payouts.outstanding_before` column) | Used its diagnosis: Neon had not received the new migration. I ran `.venv\Scriptslembic upgrade head` myself; the page worked afterwards. |
| 8 | Claude Code | "i ran the command .venv\Scriptslembic upgrade head and op: (pasted terminal output) and the payout page is fine now" | Confirmed the fix; no code change. |
| 9 | Claude Code | "go...first tell me what all things to be done for M5" | Used its plan, which split repo work from manual dashboard steps. |
| 10 | Claude Code | "C. Decisions I need from you / 1. yes / 2. do the best option / 3. yes / 4. kjbn-hackathon" | Used. The hosted deploy seeds Neon (not my machine). It generated the Dockerfiles, compose file, `render.yaml`, `vercel.json`, CI workflow and richer seed; render.yaml was validated against Render's published schema. |
| 11 | Claude Code | "all the 5 done... / https://kjbn-produce-payout-api.onrender.com / https://kjbn-hackathon-sigma.vercel.app/" | Used. It ran read-only and rejected-request checks against the hosted API and a browser pass over the hosted UI; one expectation in its own script was wrong, the app was right. |
| 12 | Claude Code | "before moving to M6, please check all the buisness rules and other things are perfect and accurate according to the Problem Statement 4 document requirements and instructions document" | Used. The audit found and fixed: a 500 on extreme `X-Test-Clock` values, missing farmer `outstanding_advance`, unescaped search wildcards, an unlogged health failure, dead model relationships, and over-long commit subjects. It added a fuzz test, rounding-invariant tests and a concurrency test. |

## Important implementation constraint
The official internship documents are the source of truth for requirements. Any assumptions must be identified explicitly, and implementation decisions must not silently introduce unsupported business rules.
