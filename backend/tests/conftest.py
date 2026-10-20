"""Test configuration. Must run before any `app` import: it points the app at the test database.

API tests need a real PostgreSQL (row locks, constraints). Start one with
`docker compose up -d db` from the repo root, or set TEST_DATABASE_URL.
"""

import os

DEFAULT_TEST_URL = "postgresql+psycopg://kjbn:kjbn_local_only@localhost:5432/kjbn_test"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_URL)

# Tests wipe every table. Refuse to run against anything that is not clearly a test database.
if not TEST_DATABASE_URL.split("?")[0].endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must point at a database whose name ends in '_test'")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ALLOW_TEST_CLOCK"] = "true"
os.environ["LOG_LEVEL"] = "WARNING"
