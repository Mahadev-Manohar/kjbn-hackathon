# SUBMISSION.md

Problem 4: Produce Procurement & Payout. Repository: <https://github.com/Mahadev-Manohar/kjbn-hackathon> · UI: <https://kjbn-hackathon-sigma.vercel.app/> · API: <https://kjbn-produce-payout-api.onrender.com/docs>

## A. What I built

I built a produce buying-centre system with a FastAPI backend, a React/TypeScript UI and a PostgreSQL database, hosted on Render, Vercel and Neon. All seven Core business rules are enforced in a pure domain layer (100% test coverage) and exposed through a versioned JSON API with OpenAPI docs. The UI has the four required screens, including a delivery form whose live preview is calculated by the backend and a weekly payout statement that shows the arithmetic down to the net amount. All Core features are complete; the partial items are that the UI has no delivery-edit screen (the API supports editing) and that there is no authentication. No Stretch items were attempted.

## B. Three design decisions

**1. Outstanding advance is derived, not stored.**
*Decision:* the balance is advances given minus recoveries on Finalised and Paid payouts. *Alternative:* a balance column on the farmer, updated at finalise. *Why:* rule 5 says reduce only when Finalised; a derived value cannot drift, and Drafts naturally do not count. *Cost:* aggregate queries on every read (two grouped queries per farmer list), and a payout must store `outstanding_before` (migration `a1c4e9d2b7f3`) so a finalised statement can still explain itself.

**2. Concurrency by a per-farmer row lock.**
*Decision:* every money-affecting use case starts with `SELECT ... FOR UPDATE` on the farmer row, then re-reads state. *Alternative:* SERIALIZABLE transactions with retries, or version columns. *Why:* easy to reason about, no retry loop, and one farmer's delivery entry, advances, generate and finalise serialise while different farmers run in parallel (tested with eight simultaneous finalises). *Cost:* it needs real PostgreSQL (SQLite was ruled out), and crop and price creation still rely on unique constraints.

**3. One pure quote function serves preview and save; rule validation lives in the domain.**
*Decision:* `quote_delivery` raises typed errors; Pydantic only checks shape and ceilings. *Alternative:* validate in the schema or database and re-implement the maths for preview. *Why:* the preview cannot disagree with the saved record, and every rule is testable without HTTP or a database. *Cost:* some checks exist twice at different strictness, so clients see two 422 codes (`validation_error`, `invalid_input`).

## C. The hardest part

The failure paths, which looked finished before they were. In M1 I gave `Delivery.crop` only a composite foreign key; SQLAlchemy could not configure the mappers, so every query would fail, but M1 only seeded data and ran skipped placeholders, so the first M3 API test found it (`036fce8`). Then I stamped domain ids onto log records; when a rule violation passed the same key through `extra=`, `logging` raised and every domain error became a 500, which seven failing API tests showed at once (`eaf3731`). Finally, after a 20-body malformed-input test passed, a fuzz test over every route found a 500 from `X-Test-Clock: 0001-01-01T00:00:00+14:00` (`931ff20`). I now test hostile input across all routes, not a sample.

## D. How I handle failure

| Case | Where it is caught | What the user sees | What is logged |
|---|---|---|---|
| Bad request | Pydantic validation | 422 `validation_error` with field list | WARNING `validation_error` (field names, no body) |
| Rule violation | typed `DomainError` raised in `app/domain`, mapped in `app/api/errors.py` | 422/404/409 with a rule-specific code and message; nothing was written | WARNING `domain_error` with code, reason, farmer/crop/payout ids |
| Database error | SQLAlchemy handlers | 409 (integrity), 422 (value range), 503 (unavailable); no SQL or driver text | WARNING/ERROR with the reason server-side |
| Unexpected exception | middleware last resort | 500 `internal_error`, generic message | ERROR with stack trace; `request_id` in both response and log |

Every response uses one shape and carries the request id. A failed request rolls back because services commit once at the end.

## E. Milestone log

| Milestone | Date completed | Commit |
|---|---|---|
| M0 Scaffold | 2026-10-18 | `1470a1b` |
| M1 Domain model | 2026-10-19 | `2685874` |
| M2 Business rules | 2026-10-20 | `4629c4b` |
| M3 API | 2026-10-20 | `521c3d3` |
| M4 UI | 2026-10-20 | `4b592d5` |
| M5 Deployment (live, CI green) | 2026-10-21 | `ff334c2` |
| M6 Documentation (README complete; `v1.0` tag is on the commit that adds this file) | 2026-10-22 | `f3c66ea` |

Later `[M3]`, `[M4]` and `[M5]` commits (for example `931ff20`, `7e40c9b`) are fixes from my pre-submission audit.

## F. If I had two more days

1. **UI: delivery-edit screen and paging controls.** The API already supports both, and this closes the only gap in the Core UI.
2. **Automated browser tests in CI.** I checked every flow with a throwaway script; committing it would protect those flows from regressions.
3. **Authentication, roles, and the test clock off by default in production.** The open API and clock override are fine for review, not for real money.
4. **Stretch: quality bonus and a printable statement.** The domain layer is built so a bonus is one more pure rule feeding `compute_payout`.
5. **Concurrency tests on several API workers plus a load test**, to confirm the row-lock design beyond a single instance.

## G. Self-assessment

| Criterion (weight) | Score | Why |
|---|---|---|
| Business logic correctness (25) | 4 | Every rule and listed edge case is enforced and tested, with Decimal money and IST dates; some interpretations (zero-delivery week is a 422, note booking week) may differ from yours. |
| Code clarity and structure (14) | 4 | Clear API / services / pure domain / persistence layers and ruff-enforced style; a few service functions are long and the test files are large. |
| Error and exception handling (10) | 5 | Distinct typed errors, one response shape, no stack traces to clients, rollback on failure, actionable UI messages, fuzz-tested. |
| Logging and observability (8) | 4 | Structured JSON with request id, domain ids and WARNING on violations, plus `/health`; hosted logs are only in the Render dashboard. |
| Data modelling and persistence (9) | 4 | Constraints, indexes, migrations checked in CI, derived advance documented; `outstanding_before` was added after the first migration. |
| API design (8) | 4 | Resource-oriented, versioned, paginated, OpenAPI; `finalise` / `mark-paid` and generate-or-refresh are action-style POSTs. |
| UI usability (6) | 4 | All flows work at laptop and 375px with loading, error and disabled states; no delivery-edit screen and plain styling. |
| Testing (7) | 5 | 182 tests with boundary cases, random rounding invariants, concurrency and fuzzing; 99% overall and 100% on the rules layer. |
| Deployment and operability (5) | 4 | One-command Compose, Dockerfiles, CI, migrate-and-seed, live and verified; manual dashboard steps and the test clock enabled in production. |
| Git hygiene (4) | 3 | Milestone commits and steady history, but three early subjects break the format (two over 72 characters, one `build` type). |
| Documentation and write-up (4) | 4 | README verified from a clean clone, with assumptions and limitations stated; the write-up is dense to fit two pages. |
