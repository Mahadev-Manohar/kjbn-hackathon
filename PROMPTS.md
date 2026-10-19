# PROMPTS.md

## Project setup and M1 — October 2026

### Project planning
- Reviewed the official internship instructions and Problem 4 specification.
- Planned implementation milestones, business rules, testing, deployment, and submission documentation.

### M0 — Scaffold
- Set up the project structure, Python backend configuration, environment examples, and Git ignore rules.

### M1 — Data model and persistence
- Defined SQLAlchemy models for farmers, crops, crop grades, price-list entries, advances, deliveries, and payouts.
- Created and applied the initial Alembic migration.
- Created an idempotent seed script using illustrative sample data.
- Documented business-rule test cases for pricing, moisture deductions, rounding, payouts, advances, and correction notes.

### Testing and review
- Checked Python syntax and Ruff formatting/linting for the seed script and business-rule specification.
- Confirmed that the business-rule test cases are currently specification placeholders; they must be implemented as executable tests in M2.
- Avoided running the seed script against the configured Neon database.

## Important implementation constraint
The official internship documents are the source of truth for requirements. Any assumptions must be identified explicitly, and implementation decisions must not silently introduce unsupported business rules.
