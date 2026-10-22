# AI-Assisted Development Log

**Project:** KJBN Labs Software Engineering Internship, Problem 4: Produce Procurement & Payout
**Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (Neon), React + TypeScript + Vite
**Tools used:** ChatGPT for M0 and M1; Claude Code from M2 onward (see README section 12)

## How to read this log

- Every prompt I sent is listed in the order I sent it, grouped by milestone, with the tool used and what I did with the result.
- All the prompts are the messages I sent to ChatGPT or Claude Code, edited only for spelling and clarity. Pasted logs, screenshots and the assignment PDFs are noted in [brackets] instead of being reproduced.
- The official KJBN Labs documents were the source of truth for requirements throughout. Assumptions are written down in the README rather than added silently.

## M0 — Scaffold

### P01 · ChatGPT · Analyze the Requirements and Establish the Project Plan

**Prompt:**

> Review the KJBN Labs assignment (the common instructions and Problem 4) and list the functional requirements, business rules, deliverables, edge cases, evaluation criteria, Git rules and any ambiguities that need numbered assumptions. Then plan milestones M0 to M6, keeping the focus on the Core requirements before any Stretch items. Treat the two PDFs as the source of truth and don't add unsupported business rules.

### P02 · ChatGPT · Define the Repository Structure

**Prompt:**

> Create the initial repository structure for Problem 4 with a layered backend (FastAPI, SQLAlchemy 2, Alembic, PostgreSQL on Neon) and a React + TypeScript + Vite frontend, hosted on Render and Vercel. Separate API routes, domain logic, services, persistence and configuration, and add folders for migrations, seed scripts and tests. Scaffold only; don't implement the API, UI or business workflows yet.

### P03 · ChatGPT · Configure the Python Backend

**Prompt:**

> Configure the Python 3.12 backend: project metadata and dependencies for FastAPI, SQLAlchemy 2, PostgreSQL, Alembic and Pydantic Settings, plus dev tools for pytest, coverage and Ruff, with runtime and dev dependencies kept separate. Make sure it installs and the tools run, and fix any setup issues.

### P04 · ChatGPT · Configure Environment Variables and Git Ignore Rules

**Prompt:**

> Add a root `.env.example` with non-secret placeholders (database URL, app environment, log level, frontend API URL) and a backend example file. Make Git ignore real `.env` files, virtual environments, caches, build output and other machine-specific files. Never copy or display real credentials, and verify the example files stay trackable.

**Outcome:** `.env` and `.venv` confirmed ignored by Git; the example files stay trackable.

### P05 · ChatGPT · Create the Initial README

**Prompt:**

> Create the initial `README.md` skeleton using the assignment's required structure. It must clearly separate what is done from what is planned, and must not claim that the API, UI, tests or deployment exist yet.

### P06 · ChatGPT · Verify and Commit the Scaffold

**Prompt:**

> Review the M0 changes, run the setup and format checks, and make sure no secrets, virtual environments or generated files are staged. Commit using the assignment's format (Conventional Commit type, `[M0]` tag, imperative subject of 72 characters or less) without squashing history, and report the hash and any limitations honestly.

**Outcome:** Committed as `1470a1b` (`chore: [M0] scaffold project and backend configuration`).

## M1 — Domain model and persistence

### P07 · ChatGPT · Translate the Domain into SQLAlchemy Models

**Prompt:**

> Implement the SQLAlchemy 2 models for farmers, crops, crop grades, effective-dated price-list entries, advances, deliveries (including correction notes) and weekly payouts, with keys, relationships, indexes, and unique and check constraints. Use Decimal-compatible types for money, weights and percentages, and enforce structural rules in the database (valid crop-grade pairs, unique effective dates, positive prices). Keep business logic out of the models.

**Outcome:** Seven model tables registered in the metadata.

### P08 · ChatGPT · Configure SQLAlchemy Database Access

**Prompt:**

> Set up the database foundation: declarative base, engine, session factory and a session dependency, with the connection string read from environment configuration. Make sure every model is registered so Alembic sees the full metadata, and check that a connection works. Use the existing Neon configuration and don't expose or overwrite credentials.

### P09 · ChatGPT · Configure Alembic and the Initial Migration

**Prompt:**

> Configure Alembic to import the full model metadata and read the connection from the environment, then generate and review the initial migration. Apply it to Neon only when appropriate and verify the revision and the tables. If the live schema and the models differ, investigate rather than generating another migration blindly.

**Outcome:** Initial migration applied to Neon; current revision `7971ae025585`.

### P10 · ChatGPT · Create an Idempotent Seed Script

**Prompt:**

> Write an idempotent `backend/scripts/seed.py` with invented farmers, crops, grades, initial prices and advances, using stable lookups so reruns create no duplicates. Document how to run it and check syntax and lint. Don't run it against the Neon database just to test it.

**Outcome:** Python syntax and Ruff checks passed. The seed was not run against Neon.

### P11 · ChatGPT · Specify the Business-Rule Test Cases

**Prompt:**

> Write a test specification for the Problem 4 rules, to be turned into real tests in M2: effective-dated pricing, moisture deductions (threshold, 10% cap, maximum accepted; equal to the maximum is accepted and above it rejected, noted as an assumption), delivery calculations with Decimal and half-up rounding, future dates, Monday–Sunday weeks, advance recovery with the 30% cap, finalisation and immutability, and credit/debit correction notes. Placeholders may stay skipped, but must be labelled as pending and never reported as passing.

**Outcome:** 17 placeholder tests collected by pytest and intentionally skipped; they were implemented in M2.

### P12 · ChatGPT · Review the Persistence Layer

**Prompt:**

> Review the models, migration and seed script against the Problem 4 requirements: the seven tables, relationships, numeric precision, uniqueness and check constraints, and whether the seed can be rerun safely. Separate real defects from cosmetic lint warnings, don't edit an applied migration, and report any unresolved discrepancies with evidence.

### P13 · ChatGPT · Maintain the Prompt Log

**Prompt:**

> Maintain a root `PROMPTS.md` that records the AI prompts for each milestone, with objectives and verification results. Keep it honest: separate reconstructed prompts from verbatim ones, and completed work from planned work.

### P14 · ChatGPT · Verify and Commit M1

**Prompt:**

> Do the final M1 review: confirm the models, Alembic setup and migration, seed script and test specification are present, run syntax, Ruff, pytest collection and whitespace checks, and check the staged files for secrets or stray artefacts. Commit in the required format with the `[M1]` tag, preserving the M0 commit.

**Outcome:** Committed as `2685874` (`feat: [M1] add domain models and business rule specifications`).

## M2 — Business rules

### P15 · Claude Code · Review the repository and assignment requirements

**Prompt**

Please review the existing repository and read both assignment documents carefully: the Common Instructions and Evaluation Criteria, and the Problem 4 statement. Treat these documents as the source of truth. I have completed M0 and M1, so continue with the remaining milestones in order, one milestone at a time. If any requirement is ambiguous or a decision is needed from me, ask before proceeding.

**Context provided:** Both assignment PDFs.

**Outcome:** Claude Code reviewed the repository and the PDFs, fixed the Ruff configuration, and implemented the M2 domain rules for pricing, moisture deductions, delivery breakdowns, payouts, and correction notes, with executable tests replacing the placeholder specifications.

## M3 — API

### P16 · Claude Code · Confirm the database and frontend approach

**Prompt**

Is SQLite necessary for this project? The schema is already set up in Neon, although it does not contain data yet, and Neon will be the hosted database. Please explain the trade-offs and recommend a development and testing setup that stays close to production. For the frontend, use React, TypeScript, and Vite.

**Outcome:** The development and test setup was changed to use local PostgreSQL through Docker, with Neon reserved for the hosted instance.

### P17 · Claude Code · Implement the API milestone

**Prompt**

Docker Desktop is running. Please proceed with M3 according to the assignment and the agreed database approach. Implement the API and service layer, validation and error handling, logging, and relevant tests. Keep the repository runnable, follow the existing architecture, and work in small, reviewable changes. Explain any important design decisions or risks as you go.

**Outcome:** Claude Code implemented the services, API routes, error handling, logging, and API tests. I reviewed the per-farmer locking design and edge-case tests. Tests identified two bugs, which were fixed.

### P18 · Claude Code · Check M3 completion

**Prompt**

Please audit M3 against its planned scope and the assignment requirements. Distinguish completed work from any remaining gaps, and identify anything that should be fixed before starting M4.

**Outcome:** The review identified unbounded ledger lists and the absence of a committed coverage report.

### P19 · Claude Code · Close the remaining M3 gaps

**Prompt**

Please address the ledger pagination gap and add the coverage report to the repository before we begin M4. Keep the response format consistent, include totals where appropriate, add or update tests, and verify the changes before committing.

**Outcome:** Ledger lists were capped and returned totals, an advances-list endpoint was added, and `scripts/coverage_report.py` was created to write `backend/coverage.txt`.

## M4 — UI

### P20 · Claude Code · Implement the frontend

**Prompt**

Please proceed with M4 using React, TypeScript, and Vite. Build the UI flows required by Problem 4 and connect them to the existing API through a dedicated API client. Include appropriate tests and handle loading, empty, validation, and error states. After implementation, exercise the main user flows in a browser and check the layout at mobile width as well as desktop width. Fix issues found during that check.

**Outcome:** Claude Code built the React + TypeScript + Vite UI, API client, and unit tests. It checked the flows in a headless browser, including at 375px width, and made layout fixes based on the findings.

## M5 — Deployment

### P21 · Claude Code · Investigate the payouts-page error

**Prompt**

Please pause M5 for now. When I open `http://localhost:5173/payouts`, the page fails. Diagnose the issue from the backend/Uvicorn log below. Trace the error to its cause before suggesting a fix, and avoid making unrelated changes.

**Context provided:** Backend error log indicating that the `payouts.outstanding_before` column was missing.

**Outcome:** The diagnosis was that the Neon database had not yet been upgraded to the latest migration.

### P22 · Claude Code · Verify the migration fix

**Prompt**

I ran `.venv\Scripts\alembic upgrade head` and have included the terminal output below. The payouts page now works. Please check whether the output confirms that the migration was applied successfully and whether any further action is needed. Do not change code unless the evidence indicates a code issue.

**Context provided:** Alembic terminal output.

**Outcome:** The migration fix was confirmed; no code change was needed.

### P23 · Claude Code · Plan the deployment milestone

**Prompt**

Please outline the complete M5 deployment checklist before making changes. Separate repository changes from manual steps in the hosting dashboards, and include the required services, environment variables, database migration and seeding strategy, CI, and verification steps. Keep the plan aligned with the assignment instructions.

**Outcome:** Claude Code listed the required repository work and manual dashboard steps.

### P24 · Claude Code · Confirm deployment decisions

**Prompt**

Here are my answers to your deployment questions: (1) Yes. (2) Choose the option you consider most appropriate for this project and explain the choice. (3) Yes. (4) Use `kjbn-hackathon` as the project/repository name. Please proceed with the deployment configuration, but make sure the hosted database is seeded by the deployment process rather than by running the seed script from my local machine. Validate the configuration against the hosting provider's requirements.

**Outcome:** Neon seeding was configured as part of the Render deployment rather than from my machine. Claude Code created the Dockerfiles, Compose file, `render.yaml`, `vercel.json`, CI workflow, and richer seed data, and validated `render.yaml` against Render's published schema.

### P25 · Claude Code · Verify the hosted application

**Prompt**

All five deployment steps are complete. Please verify the live application using the links below. Check the API with read-only requests and representative invalid requests, and exercise the main UI flows in a browser. Do not make destructive changes to the production database. Report any failures and distinguish application defects from incorrect expectations in the verification scripts.

- UI: https://kjbn-hackathon-sigma.vercel.app/
- API: https://kjbn-produce-payout-api.onrender.com

**Outcome:** Claude Code ran read-only and rejected-request checks against the live API and a browser pass over the live UI. One expectation in its verification script was incorrect; the application behaved correctly.

## M6 — Audit, documentation, and final tag

### P26 · Claude Code · Audit the implementation against the assignment

**Prompt**

Before completing M6, audit the implementation against both the Problem 4 statement and the Common Instructions and Evaluation Criteria. Check the business rules, edge cases, data integrity, error handling, concurrency, tests, deployment, and submission requirements. Fix confirmed defects, add tests where useful, and identify any remaining limitations or Git-history issues. Do not claim a requirement is satisfied unless it has been verified.

**Outcome:** The audit fixed a 500 error for extreme `X-Test-Clock` values, a missing farmer `outstanding_advance` field, unescaped search wildcards, an unlogged health-check failure, and unused model relationships. It added a fuzz test, rounding-invariant tests, and a concurrency test, and flagged three commit subjects that did not follow the required format.

### P27 · Claude Code · Recheck the hosted deployment and consolidate the prompt log

**Prompt**

I have pushed the latest commits to GitHub and checked the updated hosted site; it appears to work. Please independently recheck the hosted UI, API, and CI status. Also review the attached M0/M1 prompt log and incorporate it into the existing log, preserving the milestone order. There was also a previously identified Git-history formatting issue; assess whether it is important enough to address now, and explain the consequences before changing history.

**Context provided:** The M0/M1 prompt log as an attached text file.

**Outcome:** Claude Code rechecked CI and the live API/UI, then merged the M0/M1 prompt log into this file. The commit-subject rewrite was not performed at that stage.

### P28 · Claude Code · Prepare the required documentation

**Prompt**

I will push the new commit later. Please proceed with the documentation. Ensure the README follows the exact section order required by the Common Instructions, maps business rules to implementation and tests, and gives reproducible local setup and deployment instructions. Create `SUBMISSION.md` using the required headings and limits. Verify the instructions from a clean clone and test the Docker stack, then create the required `v1.0` tag if the repository is ready.

**Outcome:** Claude Code wrote the 12-section README, checked rule-to-code/test references automatically, verified the local setup from a clean clone and the Docker stack, wrote `SUBMISSION.md`, and created the `v1.0` tag.

### P29 · Claude Code · Decide whether to correct commit subjects

**Prompt**

Earlier, you noted that three commit subjects do not follow the required format, and that `SUBMISSION.md` and README section 11 refer to the issue. Rewriting those commit messages would change commit hashes cited in the documentation and require the tag to be recreated. Is it safe and worthwhile to correct this now? Please answer yes or no first, then briefly explain the consequences before any changes are made.

**Outcome:** Claude Code answered yes and outlined the steps and consequences.

### P30 · Claude Code · Correct the commit subjects

**Prompt**

Yes, proceed with correcting the three commit subjects. The `v1.0` tag exists only locally at this point. Preserve the commit contents, authors, and dates; verify that only the intended commit-message text changes; update any affected hashes in the documentation; and recreate the tag after verifying the resulting history.

**Outcome:** Claude Code reworded the three commit subjects with a message filter. An initial attempt introduced carriage returns on Windows and was repeated byte-exactly. The commit trees, authors, and dates were verified as unchanged, documentation hashes were refreshed, and the `v1.0` tag was recreated.

### P31 · Claude Code · Verify the push result

**Prompt**

I ran `git push --force-with-lease origin main` and `git push origin v1.0`. Please inspect the output below and verify that the remote branch and tag reflect the corrected history and that CI passes. If any part of the push did not succeed, tell me the safest next step rather than assuming it worked.

**Context provided:** Output from the two Git push commands.

**Outcome:** Claude Code verified the remote branch and tag and confirmed that CI passed on the rewritten history.

### P32 · Claude Code · Review commit attribution and the GitHub contributors display

**Prompt**

Please explain what controls the attribution shown in Git commit messages and the contributors section on GitHub. Review the attached repository screenshot and determine what can be changed without altering the source code or falsely changing authorship. If a history rewrite is appropriate, explain its impact on commit hashes, tags, and the remote branch before proceeding.

**Context provided:** Screenshot of the repository page.

**Outcome:** The attribution trailer line was removed from the 41 commit messages that contained it; trees, authors, dates, and subjects were unchanged. The hashes in `SUBMISSION.md` were refreshed and the `v1.0` tag was recreated.

### P33 · Claude Code · Troubleshoot a stuck Git sync in VS Code

**Prompt**

I accidentally clicked Pull and Push in VS Code Source Control, and the operation has appeared to load for more than 20 minutes. I intended to run `git push --force-with-lease origin main` and `git push --force origin v1.0` instead. Please help me determine whether Git is still running or the editor UI is stuck. First check the local and remote state; avoid starting overlapping Git operations. Then recommend the safest way to complete and verify the intended pushes.

**Outcome:** Claude Code checked that the local and GitHub states had not changed and determined that the spinner was stuck in the editor rather than in Git. It ran the two pushes and verified GitHub and CI.

### P34 · Claude Code · Confirm the next steps after resolving the editor issue

**Prompt**

I reloaded the VS Code window as suggested, and the interface is working normally again. Based on the current repository and submission status shown in the attached screenshot, please confirm what remains to be done and separate required actions from optional checks.

**Context provided:** Screenshot of VS Code.

**Outcome:** Claude Code confirmed the repository state and listed the remaining steps.

### P35 · Claude Code · Check whether the latest commit message can be reworded

**Prompt**

Please review the latest commit message. Can it be reworded so that it accurately describes the change without referring to the previous message-editing operation? Answer yes or no first; do not make changes until I confirm.

**Outcome:** Claude Code answered yes and described the required reword, tag recreation, and pushes.

### P36 · Claude Code · Reword the latest commit and update the prompt log

**Prompt**

Proceed with rewording the latest commit message. Update row 17 of the prompt log so its description matches the revised commit message, and check whether any related commit hashes or the `v1.0` tag need to be updated. Verify the result and push the final branch and tag.

**Outcome:** Claude Code reworded the latest commit, updated the matching prompt-log entry, added missing log entries, recreated the `v1.0` tag, and pushed the changes.

## After submission — verification and follow-up questions

### P37 · Claude Code · Test business-rule edge cases on the live site

**Prompt**

Please help me personally verify the deployed application against the assignment's edge-case checklist. Use the attached checklist covering price selection and history, moisture thresholds and deductions, weekly payouts and advance recovery, and correction notes. Give me a step-by-step procedure with the test data to enter, the expected result for each case, and cleanup or safety notes. Tell me everything I need to do, but avoid destructive actions against production data unless they are necessary and explicitly identified.

**Context provided:** The assignment checklist covering pricing, moisture, payouts, and correction cases.

**Outcome:** Claude Code produced a step-by-step test plan with expected values, which I followed on the live site.

### P38 · Claude Code · Decide which payout steps should be automated

**Prompt**

Problem 4 states that payouts are weekly, from Monday through Sunday, and should aggregate a farmer's deliveries in that week that have not already been assigned to another payout. Which parts of this workflow should happen automatically, and which should remain explicit user actions? Please explain the distinction between collecting eligible delivery lines, generating a payout, finalising it, and marking it as paid, while staying within the stated business rules.

**Outcome:** The eligible delivery lines are collected automatically when a payout is generated; generating and finalising payouts remain explicit actions.

### P39 · Claude Code · Evaluate the optional stretch features

**Prompt**

Please assess the optional stretch features: multi-centre support, a printable PDF payout statement, and a quality bonus of ₹0.50/kg for grade-A produce above a weekly threshold of X kg. For each feature, outline how it could fit the current architecture while minimizing changes to existing code paths, and identify the additional rules and tests needed. Recommend whether any should be implemented given the core assignment requirements and remaining time.

**Outcome:** I decided not to implement the stretch features. Claude Code outlined how each could fit the existing design.



## Working principles

1. **Requirements first:** the official documents define the scope and mandatory behaviour.
2. **One milestone at a time:** finish and verify each milestone before the next.
3. **Layered design:** business rules stay independent of the database and HTTP.
4. **Financial correctness:** Decimal values and the required rounding rules.
5. **Database integrity:** migrations and constraints protect stored data.
6. **Security:** no secrets or real environment files in the repository.
7. **Honest verification:** passed, failed, skipped and unexecuted checks are reported separately.
8. **Explicit assumptions:** ambiguities are documented, not silently resolved.
9. **Core before Stretch:** mandatory functionality first.
