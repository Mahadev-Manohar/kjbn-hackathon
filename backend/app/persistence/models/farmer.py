from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.base import Base


class Farmer(Base):
    __tablename__ = "farmers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    village: Mapped[str] = mapped_column(String(150), nullable=False)
    bank_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    advances: Mapped[list["Advance"]] = relationship(
        back_populates="farmer",
        lazy="raise",
    )
    deliveries: Mapped[list["Delivery"]] = relationship(
        back_populates="farmer",
        lazy="raise",
    )
    payouts: Mapped[list["Payout"]] = relationship(
        back_populates="farmer",
        lazy="raise",
    )
