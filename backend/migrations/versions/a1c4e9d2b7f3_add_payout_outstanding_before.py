"""add payout outstanding_before

Revision ID: a1c4e9d2b7f3
Revises: 7971ae025585
Create Date: 2026-10-20 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c4e9d2b7f3"
down_revision: str | Sequence[str] | None = "7971ae025585"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payouts",
        sa.Column(
            "outstanding_before",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0.00",
        ),
    )


def downgrade() -> None:
    op.drop_column("payouts", "outstanding_before")
