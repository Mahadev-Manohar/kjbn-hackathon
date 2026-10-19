from decimal import Decimal

from sqlalchemy import CheckConstraint, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.base import Base


class Crop(Base):
    __tablename__ = "crops"
    __table_args__ = (
        CheckConstraint(
            "base_moisture_threshold >= 0",
            name="ck_crops_threshold_nonnegative",
        ),
        CheckConstraint(
            "max_moisture_accepted > base_moisture_threshold",
            name="ck_crops_max_moisture_above_threshold",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    base_moisture_threshold: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    max_moisture_accepted: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    grades: Mapped[list["CropGrade"]] = relationship(
        back_populates="crop",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    price_list_entries: Mapped[list["PriceListEntry"]] = relationship(
        back_populates="crop",
        lazy="raise",
    )
