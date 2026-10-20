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

## Important implementation constraint
The official internship documents are the source of truth for requirements. Any assumptions must be identified explicitly, and implementation decisions must not silently introduce unsupported business rules.
