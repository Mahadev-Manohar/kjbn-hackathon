# AI-Assisted Development Prompt Log

**Project:** KJBN Labs Software Engineering Internship — Problem 4: Produce Procurement & Payout  
**Technology Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (Neon)  
**Milestones documented:** M0 — Scaffold Repository; M1 — Data Models, Database Migrations, Seed Data and Business-Rule Test Specifications; M2 onward — see "Claude Code" at the end

## Purpose

This document records the prompts used to plan, scaffold, and implement the application with AI assistance.

The official KJBN Labs Common Instructions and Evaluation Criteria PDF and Problem 4 specification are the authoritative sources of requirements. Implementation decisions must remain consistent with those documents. Any unavoidable assumptions must be explicitly documented rather than presented as official requirements.

**Tools:** M0 and M1 were done with ChatGPT (see README section 12). M2 onward was done with Claude Code.

**Two different kinds of record follow.** The M0 and M1 prompts below are organized by task rather than as a verbatim conversation transcript. The Claude Code section at the end lists every message in order and verbatim.

---

# M0 — Scaffold Repository and Configure the Backend

## Prompt M0.1 — Analyze the Requirements and Establish the Project Plan

**Objective:** Understand the assignment before implementing the application.

**Prompt:**

Act as a senior software engineer reviewing the KJBN Labs Software Engineering Internship take-home assignment.

Analyze the official Common Instructions and Evaluation Criteria document and the Problem 4: Produce Procurement & Payout specification.

Extract and organize:

1. Functional requirements and domain entities.
2. Mandatory business rules and validation requirements.
3. Required backend API, database, frontend, deployment, testing, and documentation deliverables.
4. Required edge cases and evaluation criteria.
5. Git workflow and milestone-specific submission requirements.
6. Ambiguities that require explicit, numbered assumptions.

Create a phased implementation plan covering milestones M0 through M6. Keep the scope focused on the mandatory Core requirements before considering optional Stretch features.

Treat the two official PDFs as the source of truth. Do not silently introduce unsupported business rules. Ensure every milestone ends in a runnable state and includes an appropriate Git commit.

## Prompt M0.2 — Define the Repository Structure

**Objective:** Establish a maintainable foundation for the application.

**Prompt:**

Design and create the initial repository structure for Problem 4 using a layered backend architecture.

Use the approved technology choices:

- Python 3.12.
- FastAPI for the backend API.
- SQLAlchemy 2 for persistence models and database access.
- Alembic for database migrations.
- PostgreSQL hosted on Neon.
- React, TypeScript, and Vite for the planned frontend.
- Render for backend hosting and Vercel for frontend hosting.

Organize the backend into clearly separated packages for API routes, domain logic, services, persistence, and application configuration. Include directories for migrations, seed scripts, and unit, API, and concurrency tests.

Keep the repository easy to navigate and ensure the structure supports later implementation of the business rules without placing calculation logic inside API routes or database models.

At this milestone, create the scaffold only. Do not prematurely implement the complete API, frontend, or business workflows.

## Prompt M0.3 — Configure the Python Backend

**Objective:** Establish reproducible backend development and testing.

**Prompt:**

Configure the Python backend for the project using Python 3.12 and a maintainable package configuration.

Set up the project metadata and dependencies for FastAPI, SQLAlchemy 2, PostgreSQL connectivity, Alembic, Pydantic Settings, and the development tools required for testing, coverage, linting, and formatting.

Configure pytest and Ruff through the project configuration file. Keep runtime dependencies separate from development dependencies where appropriate.

Ensure the backend can be installed and its development tools can be invoked through documented commands. Avoid unnecessary dependencies and do not introduce infrastructure that is outside the approved implementation plan.

Verify the configuration using the available Python environment and fix any setup issues that prevent the project from being installed or tested.

## Prompt M0.4 — Configure Environment Variables and Git Ignore Rules

**Objective:** Protect credentials and keep the repository reproducible.

**Prompt:**

Create appropriate environment-variable examples and Git ignore rules for the project.

Provide a root `.env.example` containing non-secret configuration placeholders, including the database connection setting, application environment, logging level, and frontend API base URL where applicable.

Create the backend environment example required by the backend configuration.

Ensure actual `.env` files, database credentials, virtual environments, Python caches, test caches, build output, generated files, and other machine-specific artifacts are excluded from Git.

Do not copy real credentials into example files. Do not display, commit, or replace existing secrets. Verify that the intended environment files and virtual environment directories are ignored by Git while the example files remain trackable.

## Prompt M0.5 — Create the Initial README

**Objective:** Establish the required project documentation early.

**Prompt:**

Create the initial root `README.md` for the KJBN Labs Problem 4 application.

Use the official assignment's documentation requirements to establish the required README structure. Include the project overview, problem statement, technology stack, architecture, setup instructions, configuration, testing, API documentation, business rules, assumptions, deployment, and other required sections.

At this stage, create a documentation skeleton that accurately distinguishes completed work from planned functionality.

Do not claim that the API, frontend, tests, or deployment are complete when they have not yet been implemented. Preserve the required documentation structure so later milestones can fill in verified details.

## Prompt M0.6 — Verify and Commit the Scaffold

**Objective:** Finish M0 with a clean, runnable repository.

**Prompt:**

Review the M0 changes before committing them.

Verify that the project structure, dependency configuration, environment examples, Git ignore rules, and README skeleton are present. Run the applicable setup and formatting checks.

Inspect the Git working tree and ensure that real credentials, virtual environments, and generated artifacts are not staged.

Follow the assignment's Git rules: use Conventional Commit types, include the milestone identifier in square brackets, use an imperative description, keep the subject within 72 characters, and do not squash milestone history.

Commit the completed scaffold only after the relevant checks pass. Report the commit hash and any remaining limitations accurately.

**M0 result:**

- Commit: `1470a1b`
- Commit message: `chore: [M0] scaffold project and backend configuration`

---

# M1 — Data Models, Migrations, Seed Data and Test Specifications

## Prompt M1.1 — Translate the Domain into SQLAlchemy Models

**Objective:** Represent the assignment's entities and relationships in the database.

**Prompt:**

Using the official Problem 4 specification, implement the SQLAlchemy 2 persistence models for the core domain.

Create models for:

1. Farmers.
2. Crops.
3. Crop grades.
4. Effective-dated price-list entries.
5. Farmer advances.
6. Deliveries and correction notes.
7. Weekly payouts.

Define the appropriate primary keys, foreign keys, relationships, indexes, uniqueness constraints, and check constraints.

Use suitable numeric precision for weights, percentages, prices, and monetary amounts. Represent financial values using decimal-compatible database types rather than floating-point columns.

Enforce the structural rules that belong in the database, including valid crop-grade relationships, unique effective dates for a crop and grade, positive prices, and appropriate delivery and payout constraints.

Preserve the assignment's distinction between a normal delivery and a correction note. Where the schema design requires an assumption, document it explicitly and ensure it does not contradict the official requirements.

Keep the models organized within the persistence layer. Do not implement the complete business workflow inside the ORM models.

## Prompt M1.2 — Configure SQLAlchemy Database Access

**Objective:** Connect the application to the chosen PostgreSQL database.

**Prompt:**

Implement the backend database foundation using SQLAlchemy 2 and the configured PostgreSQL connection.

Create the declarative base, engine configuration, session factory, and reusable database session dependency required by the backend.

Load the connection string from environment configuration rather than hardcoding credentials. Ensure the application imports and registers every persistence model so that Alembic can discover the complete metadata.

Use the existing Neon PostgreSQL configuration. Do not expose credentials or overwrite environment files.

Verify that the application can establish a database connection and that all expected model tables are registered in the metadata.

## Prompt M1.3 — Configure Alembic and the Initial Migration

**Objective:** Version-control the database schema.

**Prompt:**

Configure Alembic for the SQLAlchemy backend.

Set up the Alembic configuration, migration environment, and migration template. Ensure that the migration environment imports the complete model metadata and obtains the database connection from the configured environment.

Generate an initial migration representing the required core tables, relationships, constraints, and indexes.

Inspect the generated migration before applying it. Avoid unnecessary schema changes, destructive operations, or duplicate migrations.

Apply the migration to the configured Neon PostgreSQL database only when appropriate, then verify the current Alembic revision and the presence of the expected tables and constraints.

If Alembic reports a difference between the live schema and model metadata, investigate the cause rather than blindly generating or applying another migration.

## Prompt M1.4 — Create an Idempotent Seed Script

**Objective:** Prepare reproducible demonstration data.

**Prompt:**

Create `backend/scripts/seed.py` to populate the application with illustrative development data.

Include representative farmers, crops, crop grades, initial effective-dated price entries, and advance records. Use invented sample names, phone numbers, and bank references. Use clearly illustrative prices and dates rather than presenting them as real business data.

Make the script idempotent: rerunning it should not create duplicate seed records. Use stable natural keys or other appropriate lookup logic to identify existing records, and ensure related records are created in the correct order.

Use the existing SQLAlchemy models and session configuration. Handle transactions correctly and avoid embedding database credentials in the script.

Provide a documented invocation command and verify Python syntax and applicable static checks.

Do not execute the seed script against the configured Neon database merely to test the script. Choose an isolated test environment before verifying database writes.

## Prompt M1.5 — Specify the Business-Rule Test Cases

**Objective:** Record expected behaviour before implementing the domain logic.

**Prompt:**

Create a unit-test specification for the mandatory business rules in Problem 4. Organize the cases so they can be converted into executable tests during M2.

Cover the following areas:

**Effective-dated pricing**
- Select the latest price whose `effective_from` date is on or before the delivery date.
- Accept a price effective exactly on the delivery date.
- Reject a delivery if no applicable price exists.
- Ensure later price entries do not change a previously stored delivery breakdown.

**Moisture deductions**
- No deduction when moisture is equal to or below the crop threshold.
- Calculate deductions for fractional excess moisture using the required full-percentage-point rule.
- Cap the deduction at 10%.
- Accept moisture equal to the maximum accepted value and reject moisture above it, documenting the equality behaviour as an explicit assumption if needed.
- Reject invalid non-positive moisture and invalid gross weight.

**Delivery calculations**
- Calculate deduction weight using Decimal arithmetic and half-up rounding to three decimal places.
- Derive net weight from gross weight minus the stored deduction weight.
- Calculate the delivery amount using the stored net weight and applied price, rounded half-up to two decimal places.
- Test boundary and rounding cases.

**Dates and payouts**
- Reject future delivery dates using a controllable clock.
- Define Monday-to-Sunday payout-week boundaries.
- Include only eligible deliveries not already assigned to another payout.
- Test advance recovery against the outstanding balance and the 30% gross-amount limit.
- Ensure advance balances are reduced only when payouts are finalised.
- Cover zero-activity weeks, finalisation rules, and duplicate payout generation.

**Correction notes**
- Cover credit and debit sign conventions.
- Ensure correction notes reference the original delivery.
- Verify that corrections are included according to the documented payout-period rule.
- Ensure finalised payouts cannot be modified.

At M1, the tests may remain specification placeholders if the domain functions do not yet exist. Clearly label any skipped tests as pending implementation. Do not report skipped placeholders as verified business-rule tests. Implement the actual assertions and make them pass in M2.

## Prompt M1.6 — Review the Persistence Layer

**Objective:** Check that the database foundation matches the assignment.

**Prompt:**

Review the SQLAlchemy models, Alembic migration, and seed script against the official Problem 4 requirements.

Verify the seven core tables, their relationships, foreign keys, numeric precision, uniqueness rules, and check constraints. Pay particular attention to effective-dated prices, delivery breakdown persistence, correction-note references, and payout status and amount constraints.

Check that the seed script uses the current model definitions and can be rerun without intentionally duplicating seed records.

Distinguish real schema or correctness defects from cosmetic lint warnings. Do not modify an already-applied migration or make destructive database changes merely to silence a warning.

Report any unresolved structural discrepancies and the evidence needed to investigate them.

## Prompt M1.7 — Maintain the Prompt Log

**Objective:** Document AI-assisted work throughout development.

**Prompt:**

Maintain a root-level `PROMPTS.md` documenting the AI prompts used for each development milestone.

Organize the log by milestone and task. Record the objective of each prompt, the work it requested, and relevant verification outcomes.

Keep the record honest: distinguish prompts reconstructed from the development history from verbatim prompt transcripts, and distinguish completed work from planned functionality. Do not claim tests passed when they were skipped or not executed.

Update the log as work proceeds through subsequent milestones.

## Prompt M1.8 — Verify and Commit M1

**Objective:** Finish M1 with reviewable, version-controlled changes.

**Prompt:**

Perform the final M1 review before committing.

Verify that the persistence models, Alembic configuration and migration, seed script, and business-rule test specification are present. Run Python syntax checks, applicable Ruff checks, pytest collection, and staged-diff whitespace checks.

Review the staged files to ensure no credentials, virtual environments, generated database files, or unrelated artifacts are included.

Confirm that the tests explicitly marked as placeholders are skipped intentionally and are not represented as passing business-rule assertions.

Follow the required Conventional Commit format with the milestone identifier, imperative wording, and a subject no longer than 72 characters. Preserve the existing M0 commit and do not squash history.

Commit M1 only after the staged changes have been reviewed and the repository is left in a runnable state.

**M1 result:**

- Commit: `2685874`
- Commit message: `feat: [M1] add domain models and business rule specifications`

---

# Verification Record (M0 and M1)

The following records the verification performed during M0 and M1:

| Area | Recorded result |
|---|---|
| M0 scaffold | Committed as `1470a1b` |
| M1 persistence models | Seven expected model tables registered |
| Initial Alembic migration | Applied to Neon; current revision reported as `7971ae025585` |
| Seed script | Python syntax and Ruff checks passed |
| Business-rule specification | 17 placeholders collected by pytest and intentionally skipped |
| Git hygiene | `.env` and `.venv` confirmed ignored |
| M1 commit | Committed as `2685874` |

These checks establish the state of the repository at the end of M1. They do not establish that the full application, API, frontend, or all business rules were complete at that point.

---

# Development Principles Applied

1. **Requirements first:** The official internship documents define the scope and mandatory behaviour.
2. **Incremental implementation:** Complete and verify each milestone before moving to the next.
3. **Layered architecture:** Keep domain calculations independent from database and HTTP concerns.
4. **Financial correctness:** Use Decimal-compatible representations and the required rounding rules.
5. **Database integrity:** Use migrations and constraints to protect persisted data.
6. **Security:** Never commit secrets or real environment files.
7. **Honest verification:** Report passed, failed, skipped, and unexecuted checks distinctly.
8. **Traceable development:** Maintain incremental Conventional Commits without squashing milestone history.
9. **Explicit assumptions:** Document any ambiguity instead of silently adding unsupported requirements.
10. **Core before Stretch:** Complete mandatory functionality before optional enhancements.

---

# Claude Code (M2 onward)

Every message I typed to Claude Code, in order and verbatim. The first message came with the two
assignment PDFs attached (common instructions and Problem 4); message 13 came with the M0/M1
prompt log above attached as a text file. Claude Code also produced the generated code described in
the last column; I reviewed and ran it.

| # | Tool | Prompt (verbatim) | What I did with it |
|---|------|-------------------|--------------------|
| 1 | Claude Code | "Read and thoroughly understand the code till now...the 2 documents are given...read and thoroughly understand them also / if u have any dount ask me / i did milestones M0 and M1...lets continue do the remaining / lets go milestone by milestone" | Used. It reviewed the repo and PDFs, fixed the ruff config, and generated the M2 domain modules and executable tests that replaced my placeholder specs. |
| 2 | Claude Code | "is it necessary to use SQLite...tables are well set in neondb(but no data) / neon is the hosted db / yes, React + TypeScript + Vite for FE" | Used the answer: tests and local development run on a Docker PostgreSQL; Neon is used only for the hosted instance. |
| 3 | Claude Code | "i started docker desktop / go" | Used. It generated the M3 services, routers, error mapping, logging and API tests. I reviewed the per-farmer locking design and the edge-case tests. Two bugs its tests exposed were fixed (crop join mapping, log-record key collision). |
| 4 | Claude Code | "is the M3 completely done?" | Used its list of remaining gaps (unbounded ledger lists, no coverage report). |
| 5 | Claude Code | "close the ledger pagination gap and commit the coverage report before starting M4" | Used. Ledger lists are capped with counts, an advances list endpoint was added, and `scripts/coverage_report.py` writes `backend/coverage.txt`. |
| 6 | Claude Code | "go" | Used. It generated the React + TypeScript + Vite UI, API client and unit tests; its headless-browser run (21 checks incl. 375px width) led to layout fixes. |
| 7 | Claude Code | "dont start M5...got an issue on hitting http://localhost:5173/payouts" plus the pasted uvicorn error log (a missing `payouts.outstanding_before` column) | Used its diagnosis: Neon had not received the new migration. I ran `.venv\Scripts\alembic upgrade head` myself; the page worked afterwards. |
| 8 | Claude Code | "i ran the command .venv\Scripts\alembic upgrade head and op: (pasted terminal output) and the payout page is fine now" | Confirmed the fix; no code change. |
| 9 | Claude Code | "go...first tell me what all things to be done for M5" | Used its plan, which split repo work from manual dashboard steps. |
| 10 | Claude Code | "C. Decisions I need from you / 1. yes / 2. do the best option / 3. yes / 4. kjbn-hackathon" | Used. The hosted deploy seeds Neon (not my machine). It generated the Dockerfiles, compose file, `render.yaml`, `vercel.json`, CI workflow and richer seed; render.yaml was validated against Render's published schema. |
| 11 | Claude Code | "all the 5 done... / https://kjbn-produce-payout-api.onrender.com / https://kjbn-hackathon-sigma.vercel.app/" | Used. It ran read-only and rejected-request checks against the hosted API and a browser pass over the hosted UI; one expectation in its own script was wrong, the app was right. |
| 12 | Claude Code | "before moving to M6, please check all the buisness rules and other things are perfect and accurate according to the Problem Statement 4 document requirements and instructions document" | Used. The audit found and fixed: a 500 on extreme `X-Test-Clock` values, missing farmer `outstanding_advance`, unescaped search wildcards, an unlogged health failure, dead model relationships. It added a fuzz test, rounding-invariant tests and a concurrency test, and flagged three over-long or disallowed commit subjects. |
| 13 | Claude Code | "Things that still need you: / 1. i pushed the latest commits to github and checked the updated hosted site...its working good...u also check them / 2. refer the text file added / 3. do it now(if not imp leave it)" plus the attached M0 & M1 prompt log | Used. It re-checked CI and the hosted API and UI after my push, and merged my M0/M1 log into this file. The commit-subject rewrite was left undone (see notes). |
| 14 | Claude Code | "i will push the new commit later / go" | Used. It wrote the 12-section README (every rule mapped to code and tests, 58 test references checked automatically), verified the run-locally steps from a clean clone plus the Docker stack, wrote SUBMISSION.md, and created the `v1.0` tag. |
