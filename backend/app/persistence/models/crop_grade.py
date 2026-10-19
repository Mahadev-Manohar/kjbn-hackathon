from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.base import Base


class CropGrade(Base):
    __tablename__ = "crop_grades"
    __table_args__ = (UniqueConstraint("crop_id", "grade", name="uq_crop_grades_crop_grade"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crop_id: Mapped[int] = mapped_column(
        ForeignKey("crops.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    grade: Mapped[str] = mapped_column(String(20), nullable=False)

    crop: Mapped["Crop"] = relationship(
        back_populates="grades",
        lazy="raise",
    )
