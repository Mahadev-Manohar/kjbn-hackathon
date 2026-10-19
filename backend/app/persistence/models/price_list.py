from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.base import Base


class PriceListEntry(Base):
    __tablename__ = "price_list_entries"
    __table_args__ = (
        UniqueConstraint(
            "crop_id",
            "grade",
            "effective_from",
            name="uq_price_list_crop_grade_effective_from",
        ),
        CheckConstraint(
            "price_per_kg > 0",
            name="ck_price_list_price_positive",
        ),
        ForeignKeyConstraint(
            ["crop_id", "grade"],
            ["crop_grades.crop_id", "crop_grades.grade"],
            name="fk_price_list_crop_grade",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crop_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    grade: Mapped[str] = mapped_column(String(20), nullable=False)

    price_per_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    crop: Mapped["Crop"] = relationship(
        back_populates="price_list_entries",
        lazy="raise",
    )
