from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.base import Base


class PayoutStatus(str, Enum):
    DRAFT = "Draft"
    FINALISED = "Finalised"
    PAID = "Paid"


class Payout(Base):
    __tablename__ = "payouts"
    __table_args__ = (
        UniqueConstraint("farmer_id", "week_start", name="uq_payout_farmer_week"),
        CheckConstraint(
            "advance_deduction >= 0",
            name="ck_payout_advance_deduction_nonnegative",
        ),
        CheckConstraint(
            "net_amount = gross_amount - advance_deduction",
            name="ck_payout_net_amount_consistent",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("farmers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PayoutStatus] = mapped_column(
        SAEnum(PayoutStatus, name="payout_status", native_enum=False),
        nullable=False,
        default=PayoutStatus.DRAFT,
    )

    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    # Outstanding advance when the deduction was calculated; lets a finalised payout
    # show its arithmetic without replaying history.
    outstanding_before: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    advance_deduction: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    finalised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    farmer: Mapped["Farmer"] = relationship(back_populates="payouts", lazy="raise")
    deliveries: Mapped[list["Delivery"]] = relationship(
        back_populates="payout",
        lazy="raise",
    )
