from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.base import Base


class DeliveryKind(str, Enum):
    DELIVERY = "DELIVERY"
    CREDIT_NOTE = "CREDIT_NOTE"
    DEBIT_NOTE = "DEBIT_NOTE"


class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = (
        CheckConstraint(
            "(kind != 'DELIVERY') OR ("
            "gross_kg IS NOT NULL AND gross_kg > 0 AND "
            "moisture IS NOT NULL AND moisture > 0 AND "
            "deduction_pct IS NOT NULL AND deduction_pct >= 0 AND "
            "deduction_kg IS NOT NULL AND deduction_kg >= 0 AND "
            "net_kg IS NOT NULL AND net_kg >= 0 AND "
            "applied_price IS NOT NULL AND applied_price > 0 AND "
            "price_list_entry_id IS NOT NULL AND "
            "amount >= 0"
            ")",
            name="ck_deliveries_valid_breakdown",
        ),
        CheckConstraint(
            "(kind = 'DELIVERY' AND references_delivery_id IS NULL) OR "
            "(kind = 'CREDIT_NOTE' AND references_delivery_id IS NOT NULL "
            "AND amount > 0) OR "
            "(kind = 'DEBIT_NOTE' AND references_delivery_id IS NOT NULL "
            "AND amount < 0)",
            name="ck_deliveries_note_reference_and_amount",
        ),
        ForeignKeyConstraint(
            ["crop_id", "grade"],
            ["crop_grades.crop_id", "crop_grades.grade"],
            name="fk_deliveries_crop_grade",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("farmers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    crop_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    grade: Mapped[str] = mapped_column(String(20), nullable=False)

    kind: Mapped[DeliveryKind] = mapped_column(
        SAEnum(DeliveryKind, name="delivery_kind", native_enum=False),
        nullable=False,
        default=DeliveryKind.DELIVERY,
    )

    gross_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    moisture: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    deduction_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    deduction_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    net_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))

    applied_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    price_list_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_list_entries.id", ondelete="RESTRICT"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    delivered_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    payout_id: Mapped[int | None] = mapped_column(
        ForeignKey("payouts.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    references_delivery_id: Mapped[int | None] = mapped_column(
        ForeignKey("deliveries.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(Text)

    farmer: Mapped["Farmer"] = relationship(back_populates="deliveries", lazy="raise")
    # crop_id is only part of a composite FK to crop_grades, so spell out the join to crops.
    crop: Mapped["Crop"] = relationship(
        primaryjoin="Crop.id == foreign(Delivery.crop_id)",
        viewonly=True,
        lazy="raise",
    )
    payout: Mapped["Payout | None"] = relationship(back_populates="deliveries", lazy="raise")
