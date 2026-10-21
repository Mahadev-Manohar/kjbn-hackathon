# Produce Procurement & Payout

KJBN Labs Software Engineering Internship, **Problem 4: Produce Procurement & Payout**.

A buying centre records farmer deliveries (price by crop, grade and date; moisture deductions; frozen breakdowns), tracks cash advances, and produces weekly payouts that recover advances and explain every rupee down to the net amount.

Repository: <https://github.com/Mahadev-Manohar/kjbn-hackathon>

**Contents:** [2 Live links](#2-live-links) · [3 Tech stack](#3-tech-stack) · [4 Architecture](#4-architecture) · [5 Running locally](#5-running-locally) · [5a Deployment](#5a-deployment) · [6 Tests and coverage](#6-running-tests-and-coverage) · [7 API overview](#7-api-overview) · [8 Rules and assumptions](#8-business-rules-and-assumptions) · [9 Errors and logging](#9-error-handling-and-logging) · [10 Reviewer aids](#10-reviewer-aids) · [11 Known limitations](#11-known-limitations) · [12 AI and third-party usage](#12-ai-and-third-party-usage)

## 2. Live links

| What | URL |
|---|---|
| UI | <https://kjbn-hackathon-sigma.vercel.app/> |
| API base | `https://kjbn-produce-payout-api.onrender.com/api/v1` |
| API docs (OpenAPI / Swagger) | <https://kjbn-produce-payout-api.onrender.com/docs> |
| Health check | <https://kjbn-produce-payout-api.onrender.com/health> |

No login: authentication was not added (it is optional in the assignment), so there are no credentials.

**Cold start:** the API runs on Render's free tier and sleeps after about 15 minutes without traffic; the first request afterwards can take about a minute. The database (Neon free tier) also suspends after about 5 idle minutes, which adds a few seconds. If the UI says "Cannot reach the server", wait a few seconds and retry. Open `/health` first to wake both.

## 3. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 | All from the recommended list. SQLAlchemy Core/ORM with bound parameters only; no string-built SQL. |
| Database | PostgreSQL (Neon free tier in production, PostgreSQL 16 in Docker locally) | Real row locks (`SELECT ... FOR UPDATE`) are used for concurrency, so SQLite was not suitable. Schema is versioned in `backend/migrations`. |
| Frontend | React 19, TypeScript, Vite, react-router | From the recommended list. Plain CSS, no component library. |
| Tests | pytest, pytest-cov, httpx/TestClient; vitest for UI helpers | API tests run against a real PostgreSQL built from the migrations. |
| Lint / format | ruff (backend), oxlint (frontend) | Enforced in CI. |
| Hosting | API: Render (Docker, free). UI: Vercel (free). DB: Neon (free) | All from the recommended list. |
| Containers / CI | Docker + Compose, nginx for the UI image, GitHub Actions | Required by deliverable D5. |

No non-recommended technology was used, so no extra justification is needed.

## 4. Architecture

```
 Browser (React SPA)                          GitHub Actions (CI: lint, migrations check, tests, build)
   |  JSON over HTTPS, optional X-Test-Clock
   v
 FastAPI app (Render / Docker)
   Request-id + logging middleware  ->  CORS  ->  router (app/api)
        |                                              |
        |  one error shape                             v
        |                                      service / use case (app/services)
        |                                        - transaction + per-farmer row lock
        |                                              |            |
        |                                              v            v
        |                                   domain rules       persistence (app/persistence)
        |                                   (app/domain, pure)   SQLAlchemy -> PostgreSQL (Neon)
        v
   {"error": {code, message, details, request_id}}
```

Request flow, e.g. saving a delivery: the router validates the body (Pydantic) and builds a request object; the service takes the farmer lock, loads the crop and price candidates, calls the **same** `quote_delivery` function the preview uses, inserts the delivery with its frozen breakdown, re-syncs any Draft payout for that week, commits, and returns the stored row.

### Folders

| Folder | Purpose |
|---|---|
| `backend/app/domain/` | **Business rules.** Pure Python (standard library only, no HTTP or database imports): pricing, moisture deduction, breakdown, payout and advance maths, note and immutability rules, the clock. |
| `backend/app/services/` | Use cases: transactions, locking, loading data, calling the rules, persisting results. |
| `backend/app/persistence/` | SQLAlchemy models, session, and reusable queries. No business decisions. |
| `backend/app/api/` | HTTP only: routers, request/response schemas, error mapping, middleware, dependencies. |
| `backend/app/core/` | Settings (environment variables) and structured logging. |
| `backend/migrations/` | Alembic migrations (schema is never created by hand). |
| `backend/scripts/` | `seed.py`, `migrate_and_seed.py` (used by Docker and Render), `coverage_report.py`. |
| `backend/tests/` | `unit/` (rules, no database) and `api/` (HTTP against PostgreSQL). |
| `frontend/` | React + TypeScript UI (`src/api`, `src/lib`, `src/hooks`, `src/components`, `src/pages`), Dockerfile, nginx config, `vercel.json`. |
| `.github/workflows/` | CI. |
| Repo root | `docker-compose.yml`, `render.yaml`, `.env.example`, `README.md`, `SUBMISSION.md`, `PROMPTS.md`. |

### Where the business rules live, and why

All rules are in `backend/app/domain/`, enforced by the backend; the UI only displays results. Keeping them pure means every rule is a fast unit test with no database or server, and the delivery **preview and save cannot disagree** because both call `delivery_rules.quote_delivery`. The database adds structural guarantees (unique `(farmer, week)`, unique price dates, positive prices, note sign checks), and services add what needs state: locking and "is this week finalised".

## 5. Running locally

### Prerequisites

| Tool | Version tested |
|---|---|
| Python | 3.12 |
| Node.js / npm | 24 / 11 |
| Docker Desktop with Compose v2 | 29 / 5 (needed for the database; also runs the whole stack) |

### Environment variables

Copy the root `.env.example` to **`backend/.env`** (the backend reads `.env` from its own folder). Real `.env` files are git-ignored.

| Variable | Meaning | Local value |
|---|---|---|
| `DATABASE_URL` | PostgreSQL URL. `postgres://` and `postgresql://` are accepted and converted to the psycopg driver. | `postgresql+psycopg://kjbn:kjbn_local_only@localhost:5432/kjbn_dev` |
| `APP_ENV` | Label written to logs. | `development` |
| `LOG_LEVEL` | Python log level. | `INFO` |
| `CORS_ORIGINS` | Comma-separated UI origins allowed by CORS. | `http://localhost:5173` |
| `ALLOW_TEST_CLOCK` | Honour the `X-Test-Clock` header (reviewer aid). | `true` |
| `TEST_DATABASE_URL` | Tests only. Must end in `_test`; it is wiped on every run. | `postgresql+psycopg://kjbn:kjbn_local_only@localhost:5432/kjbn_test` |
| `SEED_ON_START` | Docker/Render start-up: `false` migrates without seeding. | `true` |
| `VITE_API_BASE_URL` (frontend) | API base URL, no trailing slash. `npm run dev` falls back to `http://localhost:8001` if unset; production builds require it. | `http://localhost:8001` |

**Careful:** if `backend/.env` points at your hosted Neon database, the backend uses it. Point it at the local database for development.

### Option A: everything with one command

```
docker compose up --build
```

UI <http://localhost:8080>, API <http://localhost:8002> (docs at `/docs`). The API container applies migrations and the seed on start. Ports differ from the dev servers below so both can run together. Stop with `docker compose down` (add `-v` to wipe the database).

### Option B: backend and UI separately

```
# 1. database only (also provides the kjbn_test database)
docker compose up -d db

# 2. backend (from the repo root; PowerShell shown, use source .venv/bin/activate on macOS/Linux)
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy ..\.env.example .env          # then set DATABASE_URL to the local value above
python -m scripts.migrate_and_seed # migrate + seed (or: alembic upgrade head ; python -m scripts.seed)
uvicorn app.main:app --reload --port 8001

# 3. UI (second terminal, from the repo root)
cd frontend
copy .env.example .env
npm ci
npm run dev                        # http://localhost:5173
```

One command each: backend `uvicorn app.main:app --reload --port 8001`, UI `npm run dev`, tests `python -m pytest` (see section 6).

## 5a. Deployment

The hosted instance is: **API on Render** (Docker), **UI on Vercel**, **database on Neon**. Everything below is committed; the manual dashboard steps are marked.

| File | Used for |
|---|---|
| `backend/Dockerfile` | API image (non-root user). Start command runs `python -m scripts.migrate_and_seed`, then `uvicorn` on `$PORT`. |
| `frontend/Dockerfile`, `frontend/nginx.conf` | UI image for Docker/Compose (`VITE_API_BASE_URL` is a build argument). |
| `docker-compose.yml` | Local database, or the whole stack. |
| `render.yaml` | Render Blueprint for the API (validated against Render's published schema). |
| `frontend/vercel.json` | Vercel build settings and the single-page-app rewrite. |
| `.github/workflows/ci.yml` | Lint, migration/model check, tests with a coverage gate, frontend lint/test/build. |
| `backend/scripts/migrate_and_seed.py` | Idempotent migrate-and-seed, run on every API start. |

### Steps used (clean clone to live)

1. **(Manual, Neon)** Create a Neon project and copy its connection string (the direct, non-pooled one is simplest).
2. **(Manual, GitHub)** Push this repository to a public GitHub repo.
3. **(Manual, Render)** New, then Blueprint, select the repo. Render reads `render.yaml`. In the dashboard, enter `DATABASE_URL` (the Neon string) and `CORS_ORIGINS` (temporary value). Choose the region nearest the Neon project. On first start the logs show the migrations, then `seed_complete`.
4. **(Manual, Vercel)** Import the repo, set **Root Directory** to `frontend`, add the environment variable `VITE_API_BASE_URL` = the Render URL (no trailing slash), deploy.
5. **(Manual, Render)** Set `CORS_ORIGINS` to the exact Vercel origin (no trailing slash; comma-separate several). The service restarts.
6. Check `/health`, `/docs`, then open the UI.

### Redeploy after a code change

Push to `main`: Render and Vercel both deploy automatically, and CI runs. Migrations are applied by the API start-up script, so a new migration needs no manual step.

### Re-seed

The seed is idempotent: reference data (farmers, crops, grades, prices, advances) is inserted only where missing, and the demo activity (deliveries, payouts, a note) is created only when **no deliveries exist**. To restore the pristine demo data after testing, run this in the Neon SQL editor, then trigger a redeploy (Render, Manual Deploy) or restart the service:

```sql
TRUNCATE deliveries, payouts, advances, price_list_entries, crop_grades, crops, farmers
  RESTART IDENTITY CASCADE;
```

Locally the same works with `docker compose exec db psql -U kjbn -d kjbn_dev`, then `python -m scripts.migrate_and_seed`. Free Neon databases pause when idle; they wake on the first query, and nothing needs re-seeding.

### Where logs are on the hosted instance

Render dashboard, service `kjbn-produce-payout-api`, **Logs** tab (JSON lines, one per request plus events). They are not publicly readable.

## 6. Running tests and coverage

```
docker compose up -d db          # API tests need PostgreSQL (kjbn_test is created automatically)
cd backend
python -m pytest                 # 182 tests
python -m scripts.coverage_report   # runs the tests with coverage and rewrites backend/coverage.txt
```

Frontend: `cd frontend && npm test` (15 tests), plus `npm run lint` and `npm run build`.

| Measure | Result (latest run, `backend/coverage.txt`) |
|---|---|
| Backend tests | 182 passed |
| Backend coverage, overall (`app/`) | **99%** (1,257 statements, 1 missed) |
| Business-rules layer (`app/domain/`) | **100%** (239 statements, 0 missed); the target was at least 80% |
| Frontend unit tests | 15 passed |

**What is covered:** every business rule at its boundaries (unit tests, no database); the whole HTTP API against real PostgreSQL built from the Alembic migrations; concurrency (eight simultaneous finalises, generates, duplicate price inserts, delivery entry racing a finalise); a fuzz test that sends hostile values to every route and asserts "never a 5xx"; the seed (figures, idempotence); error shapes, safe 5xx bodies, request ids and log contents; CORS.

**What is deliberately not covered:** the single uncovered backend line (`app/api/errors.py`, the fallback for a domain error type with no mapped status) cannot be reached today; coverage only measures `app/`, not `scripts/` or migrations (the migration is exercised by every API test run and by `alembic check` in CI); React components have no automated tests (their behaviour was checked in a real browser against both the local and the hosted deployment; that script is not part of the repository); `uvicorn` and the Render/Vercel/Neon platforms are not tested here.

CI (`.github/workflows/ci.yml`) runs ruff, `alembic upgrade head` plus `alembic check`, the tests, and fails if the rules layer drops below 80%; the frontend job runs lint, tests and build.

## 7. API overview

Base path `/api/v1`. Interactive docs and the OpenAPI schema: `/docs`, `/openapi.json`. Money, weights and percentages are JSON **strings** (exact decimals). List endpoints return `{items, total, limit, offset}` with `limit` capped at 200.

| Method | Path | Purpose | Main error codes |
|---|---|---|---|
| GET | `/health` (no prefix) | Liveness plus a database round trip | 503 `database_unavailable` |
| POST | `/farmers` | Create a farmer | 422 `validation_error` |
| GET | `/farmers` | List/search farmers (`q`, `limit`, `offset`); includes derived `outstanding_advance` | 422 |
| GET | `/farmers/{id}` | One farmer | 404 `not_found` |
| PATCH | `/farmers/{id}` | Update fields | 404, 422 |
| POST | `/farmers/{id}/advances` | Record an advance | 404, 422 `advance_in_future` |
| GET | `/farmers/{id}/advances` | Paginated advances | 404 |
| GET | `/farmers/{id}/ledger` | Balances plus newest `limit` deliveries, advances, payouts | 404 |
| POST | `/crops` | Create crop with grades and moisture limits | 409 `crop_exists`, 422 |
| GET | `/crops`, `/crops/{id}` | List / one crop | 404 |
| PATCH | `/crops/{id}` | Change moisture limits (future deliveries only) | 404, 422 |
| POST | `/crops/{id}/grades` | Add an allowed grade | 404, 409 `grade_exists` |
| POST | `/price-list` | Append a price entry (back-dating allowed; never overwrites) | 404, 409 `price_exists`, 422 |
| GET | `/price-list` | Price history, newest first per crop and grade (`crop_id`, `grade`) | 422 |
| POST | `/deliveries/preview` | Price, deduction and amount without saving | 404, 422 `price_not_found`, `moisture_above_maximum`, `delivery_in_future`, `week_already_finalised`, `invalid_input` |
| POST | `/deliveries` | Create a delivery; returns the full frozen breakdown | same as preview |
| GET | `/deliveries` | List (`farmer_id`, `crop_id`, `date_from`, `date_to`) | 422 |
| GET | `/deliveries/{id}` | One delivery or note | 404 |
| PUT | `/deliveries/{id}` | Edit a delivery not in a Finalised/Paid payout; breakdown is re-frozen | 404, 422 `delivery_locked`, `note_not_editable` |
| POST | `/deliveries/{id}/notes` | Credit or debit note for a delivery in a Finalised/Paid payout | 404, 422 `note_target_not_finalised`, `note_target_invalid` |
| POST | `/payouts` | Generate the Draft for `{farmer_id, week_start}` or refresh it (201 new, 200 refreshed) | 404, 409 `payout_immutable`, 422 `week_start_not_monday`, `week_in_future`, `no_deliveries_in_week` |
| GET | `/payouts` | List (`farmer_id`, `status`, `week_start`) | 422 |
| GET | `/payouts/{id}` | Statement: every line and the arithmetic to the net | 404 |
| POST | `/payouts/{id}/finalise` | Draft to Finalised; applies the advance recovery | 404, 409 `invalid_payout_transition`, 422 `no_deliveries_in_week` |
| POST | `/payouts/{id}/mark-paid` | Finalised to Paid | 404, 409 `invalid_payout_transition` |

Requests accept `X-Request-ID` (echoed back) and `X-Test-Clock` (section 10).

## 8. Business rules and assumptions

### Rules from the Problem 4 document

Paths are under `backend/`. "dr / dc / pr / nr" are the unit-test files `tests/unit/test_delivery_rules.py`, `test_delivery_calculations.py`, `test_payout_rules.py`, `test_note_rules.py`; API tests are in `tests/api/`.

| # | Rule | Enforced in | Tests |
|---|---|---|---|
| 1 | Price = entry with latest `effective_from` on or before the delivery date; none means rejection naming the combination | `app/domain/delivery_calculations.py::select_applicable_price`; message built in `delivery_rules.py::quote_delivery` | dc `test_latest_applicable_price_is_selected`, `test_price_effective_on_delivery_date_is_eligible`, `test_missing_applicable_price_is_rejected`; dr `test_missing_price_message_names_crop_grade_and_date`; API `test_delivery_on_exact_effective_date_uses_new_price`, `test_missing_price_names_the_combination` |
| 2 | Deduct 1% of gross per full 1% above the crop threshold, cap 10%; above the crop maximum is rejected | `delivery_calculations.py::calculate_deduction_percentage` | dc `test_deduction_percentage` (14.00, 14.99, 15.00, 17.60, 24.99), `test_maximum_accepted_moisture_is_allowed`, `test_moisture_above_maximum_is_rejected`; API `test_moisture_exactly_at_threshold_has_no_deduction`, `test_moisture_just_below_next_percent_point_is_not_deducted`, `test_moisture_above_crop_maximum_is_rejected` |
| 3 | Every delivery stores a frozen breakdown (gross, deduction %, deduction kg, net kg, applied price, price entry id, amount half-up to 2 dp); later price edits do not change it | `delivery_calculations.py::calculate_delivery_breakdown`, `delivery_rules.py::quote_delivery`; stored by `app/services/deliveries.py`; price list is append-only (`app/services/master_data.py::add_price`, no update or delete route) | dc `test_delivery_breakdown`, `test_deduction_weight_uses_half_up_rounding`, `test_amount_uses_half_up_rounding`, `test_deduction_weight_tie_rounds_half_up_not_to_even`, `test_breakdown_invariants_hold_for_many_random_inputs`; API `test_create_delivery_returns_full_breakdown`, `test_back_dated_price_does_not_change_existing_deliveries`, `test_price_history_is_append_only_and_ordered` |
| 4 | Weekly (Monday to Sunday) payout aggregates a farmer's deliveries in that week not already in another payout | `app/domain/payout_rules.py::week_start`; `app/services/payouts.py::sync_payout`; `app/persistence/queries.py::unassigned_lines_in_week`; unique `(farmer_id, week_start)` | pr `test_week_boundaries_are_monday_to_sunday`, `test_week_crossing_month_end`; API `test_payout_statement_shows_every_line_and_the_arithmetic`, `test_regenerating_a_draft_refreshes_it_and_creates_no_duplicate`, `test_concurrent_payout_generation_creates_one_payout` |
| 5 | Recovery = lesser of outstanding advance and 30% of gross; outstanding is reduced only when Finalised | `payout_rules.py::advance_recovery`, `recovery_cap`, `outstanding_advance`; outstanding is derived in `queries.py::recovered_advances` from Finalised/Paid payouts only | pr `test_recovery_is_capped_at_30_percent_of_gross`, `test_recovery_is_capped_at_outstanding_balance`, `test_recovery_cap_rounds_half_up`, `test_large_advance_is_recovered_at_30_percent_over_several_payouts`; API `test_advance_is_reduced_only_when_the_payout_is_finalised`, `test_advance_larger_than_30_percent_is_recovered_over_several_payouts`, `test_two_drafts_cannot_over_recover_one_advance`, `test_concurrent_finalise_recovers_the_advance_exactly_once` |
| 6 | A Finalised payout is immutable; its deliveries cannot be edited; corrections are credit/debit note deliveries referencing the original and landing in the next payout | `payout_rules.py::ensure_draft`, `ensure_can_finalise`, `ensure_can_mark_paid`; `app/domain/note_rules.py::ensure_delivery_editable`, `ensure_note_target`, `signed_note_amount`, `note_effective_date`, `ensure_week_open_for_delivery` | pr `test_finalised_or_paid_payout_is_immutable`; nr `test_delivery_in_finalised_payout_cannot_be_edited`, `test_note_must_reference_a_finalised_delivery`, `test_note_moves_to_next_open_week_when_current_week_is_finalised`; API `test_finalised_payout_is_immutable_for_its_deliveries`, `test_credit_note_lands_in_the_next_payout`, `test_debit_note_is_deducted_in_the_next_payout`, `test_note_rules_are_enforced` |
| 7 | Grade must be an allowed grade; weight and moisture positive; future date rejected | `delivery_rules.py::validate_delivery_request` (date uses the IST "today" from the request clock) | dr `test_grade_outside_allowed_list_is_rejected`, `test_invalid_weight_is_rejected`, `test_invalid_moisture_is_rejected`, `test_future_delivery_date_is_rejected`; API `test_future_delivery_is_rejected_against_the_request_clock`, `test_grade_not_allowed_for_crop_is_rejected` |

### Edge cases listed in the problem

| Edge case | Test |
|---|---|
| Delivery on the exact `effective_from` date | dr `test_delivery_on_exact_effective_from_uses_new_price`, `test_day_before_effective_from_uses_previous_price` |
| Moisture exactly at the threshold and at 14.99% | API `test_moisture_exactly_at_threshold_has_no_deduction`, `test_moisture_just_below_next_percent_point_is_not_deducted` |
| Advance larger than 30% of several payouts in a row | API `test_advance_larger_than_30_percent_is_recovered_over_several_payouts` |
| Back-dated price entry after deliveries exist | API `test_back_dated_price_does_not_change_existing_deliveries`; dr `test_back_dated_price_entry_selected_for_matching_delivery_date` |
| A week with zero deliveries | pr `test_week_without_deliveries_is_rejected`; API `test_week_with_no_deliveries_is_rejected` |
| Rounding differences across the breakdown (net equals the sum of the parts) | API `test_breakdown_parts_add_up_across_awkward_weights`; dc `test_breakdown_invariants_hold_for_many_random_inputs` |

### Assumptions

1. **Decimals only.** Money, weights and percentages are `Decimal` in code and `NUMERIC` in the database, serialised as strings. JSON numbers such as `33.333` are read exactly (`test_json_numbers_are_read_exactly_not_through_binary_floats`).
2. **Precision limits.** Weight allows at most 3 decimal places and moisture at most 2; finer values are rejected (rounding 14.999 up would change the deduction). Sanity ceilings keep values inside their columns: weight at most 100,000 kg, price at most 10,000 per kg, advance and note amounts at most 10,000,000.
3. **Rounding.** Deduction kg is rounded half-up to 3 dp; net kg is gross minus that stored deduction, so the parts always add up exactly; amount is net kg times price rounded half-up to 2 dp.
4. **Threshold and maximum.** Moisture equal to the threshold has no deduction. Moisture equal to the crop maximum is accepted (deduction capped at 10%); only values above it are rejected.
5. **Grades are case-sensitive** (`a` is not `A`).
6. **"Today" is the IST calendar date.** Timestamps are stored in UTC (`timestamptz`) and shown in IST by the UI; business dates (`delivered_on`, `given_on`, `week_start`) are IST calendar dates. The future-date rule compares against the request clock (section 10).
7. **Outstanding advance is derived, never stored:** advances given minus `advance_deduction` of Finalised and Paid payouts. A Draft changes nothing (rule 5).
8. **The 30% cap** is rounded half-up to the paisa and applies to the payout's gross including credit and debit notes. If gross is zero or negative, nothing is recovered.
9. **One payout per farmer per week**, requested by the week's Monday. A non-Monday date, or a week that has not started, is rejected.
10. **Drafts stay in sync.** Creating or editing a delivery, adding a note, or recording an advance refreshes that farmer's Draft payouts automatically. Finalising recalculates against the advance outstanding at that moment, so two Drafts can never recover the same advance twice.
11. **A week with no unpaid deliveries** returns a clear 422 (`no_deliveries_in_week`) and creates no payout row.
12. **No new delivery may join a week whose payout is Finalised or Paid** (422 `week_already_finalised`, pointing to credit/debit notes). Likewise a delivery cannot be moved into such a week.
13. **Editing a delivery** (allowed until its payout is Finalised) re-freezes its breakdown using the price list as it stands at edit time. Rule 3 protects deliveries from later price-list changes, not from deliberate edits of the delivery itself.
14. **Credit and debit notes.** A credit note adds money for the farmer (positive), a debit note deducts (stored negative). The amount is entered directly, positive, up to 2 dp. A note must reference an original delivery (not another note) in a Finalised or Paid payout, and cannot be edited. "Next payout" means the payout for the week the note is booked in: today's IST date, or the next Monday whose week is not already Finalised or Paid for that farmer.
15. **A payout can be negative** if debit notes outweigh the week's deliveries; nothing is recovered and nothing carries forward.
16. **Price list is append-only.** Back-dated entries are allowed; a second entry for the same crop, grade and date is a 409. Changing a crop's moisture limits affects only future deliveries.
17. **Status changes are forward-only:** Draft, then Finalised, then Paid.
18. **An advance cannot be dated in the future.**
19. **Phone numbers** are 10 to 15 digits with an optional leading `+` and are not required to be unique (family members share phones).
20. **No authentication.** The reviewer clock override is deliberately enabled on the hosted instance.
21. **Lists are bounded.** `limit` is at most 200; the ledger returns exact balances plus the newest `limit` rows of each list with totals.

## 9. Error handling and logging

### Error response shape

Every failure, including unknown routes, uses one JSON shape and an `X-Request-ID` response header carrying the same id:

```json
{"error": {"code": "price_not_found",
           "message": "No price list entry for Maize grade A effective on or before 2025-12-31",
           "details": {"crop": "Maize", "grade": "A"},
           "request_id": "4b8ef5aa4c5948488239a6be7d33b278"}}
```

### Which error is which

| Kind | Raised as | HTTP | `code` | Example |
|---|---|---|---|---|
| Malformed request (wrong type, missing field, unknown field, out-of-range number) | Pydantic validation | 422 | `validation_error` with `details.fields` | `gross_kg: "abc"` |
| Input that parses but is invalid | `InvalidInputError` (`app/domain/errors.py`) | 422 | `invalid_input` | grade not allowed, weight with 4 decimals |
| Business rule violated | `RuleViolationError` | 422 | rule-specific (`price_not_found`, `moisture_above_maximum`, `delivery_in_future`, `delivery_locked`, ...) | moisture above the crop maximum |
| Missing entity | `NotFoundError` | 404 | `not_found` | unknown farmer or payout |
| State conflict | `ConflictError` | 409 | `conflict`, `payout_immutable`, `invalid_payout_transition`, `price_exists`, ... | regenerating a Finalised payout |
| Database integrity (race on a unique constraint) | `IntegrityError` | 409 | `conflict` | two simultaneous identical price entries |
| Value outside what the database can store | `DataError` | 422 | `value_out_of_range` | integer id larger than 4 bytes |
| Database unreachable | `OperationalError` | 503 | `database_unavailable` | Neon down |
| Anything else | middleware last resort | 500 | `internal_error` | generic message, no internals |

Responses never contain stack traces, SQL, or exception text for database and unexpected errors. Services commit once at the end of a use case; an exception leaves the session to roll back, so a failed request writes nothing.

### Logging

Structured JSON, one line per event, to stdout. Fields on every line: `timestamp` (UTC), `level`, `logger`, `event`, `request_id`. Per request the middleware logs `request` with method, path, status and `duration_ms`; the request/correlation id comes from the `X-Request-ID` header if supplied (short printable values only) or is generated. Lookups attach domain identifiers (`farmer_id`, `crop_id`, `delivery_id`, `payout_id`) to every log line of that request.

| Level | What |
|---|---|
| INFO | One `request` line per request; business events: `delivery_created`, `payout_generated`, `payout_finalised`, `payout_paid`, `note_created`, `advance_recorded`, `price_added`, `farmer_created`, ... |
| WARNING | Rule violations (`domain_error` with `code`, `reason`, ids), validation errors (field names only), integrity and data errors |
| ERROR | `unhandled_exception` with the stack trace (server-side only), `database_unavailable`, `health_check_failed` |

Request and response bodies, names, phone numbers, bank references and credentials are never logged. On the hosted instance, logs are in the Render dashboard (Logs tab).

## 10. Reviewer aids

**Test clock.** Time-based rules (future dates, "week has started", which week a note lands in) depend on "today". Override it without waiting:

- Header: `X-Test-Clock: 2026-10-20` (a date means noon IST) or `X-Test-Clock: 2026-10-20T10:00:00+05:30` (no offset means IST).
- UI: the **Reviewer clock** bar under the title bar. Enter a value, press Set; it is stored in the browser and sent with every call. Use "Use real time" to clear it.
- Invalid values return 422 naming the header. It is honoured only when `ALLOW_TEST_CLOCK=true` (it is, on the hosted instance). Timestamps such as `finalised_at` use the same clock.

**Seed data** (invented names; prices are illustrative):

| Farmer | State to try |
|---|---|
| Arun Kumar (₹25,000 advance) | Week of 28 Sep **Paid**, 5 Oct **Finalised**, 12 Oct **Draft**; a credit note booked in the current week; large advance shows the 30% cap. Weeks before 12 Oct are locked, so a new delivery there is refused. |
| Meena Devi (₹800 advance) | Advance recovered in full in one payout (the "lesser of" rule); 12 Oct Draft. |
| Ravi Selvan (₹2,000 advance) | Two deliveries, **no payouts**: generate one, finalise it, then issue a note. |
| Lakshmi Narayanan, Kavitha Raj | No activity: add deliveries from scratch. |

Maize A has two prices (₹24.00 from 1 Jan, ₹25.50 from 5 Oct) and Turmeric A two (₹120 and ₹125 from 1 Oct): a delivery dated 4 Oct versus 5 Oct shows the effective-date switch.

**Quick API checks** (no data is changed by previews):

```
curl -X POST https://kjbn-produce-payout-api.onrender.com/api/v1/deliveries/preview \
  -H "Content-Type: application/json" -H "X-Test-Clock: 2026-10-21" \
  -d '{"crop_id":1,"grade":"A","gross_kg":"100","moisture":"17.6","delivered_on":"2026-10-02"}'
# 3% deduction, price 24.00, amount 2328.00; change delivered_on to 2026-10-06 for price 25.50
```

**Re-seed / reset:** section 5a. **Interactive docs:** `/docs`. **Coverage summary:** `backend/coverage.txt`.

## 11. Known limitations

- **No delivery-edit screen in the UI.** Editing is available only through the API (`PUT /deliveries/{id}`); the UI offers entry, preview, and credit/debit notes.
- **No authentication or roles.** Every endpoint is open, and the test-clock override is enabled on the hosted instance on purpose. Nothing can be deleted through the API.
- **Free-tier cold starts** (about a minute for Render, a few seconds for Neon) and no persistent disk.
- **A week with no deliveries returns a 422** instead of creating an empty payout; this is an interpretation (assumption 11). Negative payouts are possible and are not carried forward (assumption 15).
- **UI paging is basic.** Dropdowns load at most 200 farmers; payout lists load at most 100; the ledger shows the newest 50 rows of each list. The API paginates fully.
- **Concurrency is tested on a single API instance** with the per-farmer row lock. Crop and price creation rely on database unique constraints (tested with simultaneous inserts), not locks.
- **The test clock also stamps `finalised_at` and `paid_at`**, so those timestamps reflect the overridden clock when it is used. The seed's timestamps are a fixed instant (20 Oct 2026, 10:00 IST).
- **React components have no automated tests**; only the formatting helpers and the API client do. UI behaviour was checked manually and with a browser script that is not in the repository.
- **Stretch items were not attempted** (multi-centre, PDF statement, quality bonus).
- **Git history:** three early commit subjects do not follow the commit format exactly (two are 3 to 4 characters over 72, and one uses the type `build`, which is not in the allowed list). The history was not rewritten after publication.

## 12. AI and third-party usage

**AI assistants.** ChatGPT was used for M0 and M1 (planning, scaffold, models, migration, seed, test specifications). Claude Code was used from M2 onward: the domain rules and their tests, services and API, error handling and logging, the React UI, the Docker/CI/Render/Vercel files, deployment checks, the audit before this milestone, and this documentation. I reviewed, ran and can explain the code; the business rules are the part I am answerable for line by line. The complete prompt log, with every message to Claude Code verbatim and the reconstructed M0/M1 prompts, is in [`PROMPTS.md`](PROMPTS.md).

**Templates and snippets.** The frontend was scaffolded with the official Vite `react-ts` template (`npm create vite`); its demo content was removed. Alembic's generated `env.py`/`script.py.mako` were adapted. No code was copied from another project or candidate.

**Libraries.** Backend: FastAPI, Starlette, Uvicorn, SQLAlchemy, Alembic, psycopg 3, Pydantic and pydantic-settings, python-dotenv; dev tools pytest, pytest-cov, httpx, ruff. Frontend: React, react-dom, react-router-dom, Vite, TypeScript, vitest, oxlint. Infrastructure: PostgreSQL, nginx, Docker, GitHub Actions. Hosting: Render, Vercel, Neon.
