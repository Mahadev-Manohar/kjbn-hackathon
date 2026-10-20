"""Bring a database up to date and load sample data. Used by Docker and the hosted deploy.

Run from the backend directory:
    python -m scripts.migrate_and_seed

Both steps are idempotent: migrations only apply what is pending, and the seed only inserts what
is missing. Set SEED_ON_START=false to migrate without seeding.
"""

import logging
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.logging import configure_logging
from scripts.seed import seed

BACKEND_DIR = Path(__file__).resolve().parents[1]
logger = logging.getLogger("scripts.migrate_and_seed")


def main() -> None:
    configure_logging(os.environ.get("LOG_LEVEL", "INFO"))
    logger.info("migrating")
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    logger.info("migrated")
    if os.environ.get("SEED_ON_START", "true").lower() == "true":
        seed()


if __name__ == "__main__":
    main()
