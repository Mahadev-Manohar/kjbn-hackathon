from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.base import Base


class Advance(Base):
    __tablename__ = "advances"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_advances_amount_positive"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("farmers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    given_on: Mapped[date] = mapped_column(Date, nullable=False)

    farmer: Mapped["Farmer"] = relationship(
        back_populates="advances",
        lazy="raise",
    )
