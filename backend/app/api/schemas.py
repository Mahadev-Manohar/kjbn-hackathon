"""Request and response models. Money and weights travel as JSON strings (exact decimals)."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from pydantic import (
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
)

from app.domain.payout_rules import recovery_cap
from app.persistence.models import DeliveryKind, PayoutStatus

# Upper bounds keep every value inside its NUMERIC column (amount = kg x price <= 10^9).
MAX_WEIGHT_KG = Decimal("100000")
MAX_PRICE_PER_KG = Decimal("10000")
MAX_MONEY = Decimal("10000000")

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
GradeCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=20, pattern=r"^[A-Za-z0-9+\-]+$"
    ),
]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9]{10,15}$")]
Weight = Annotated[Decimal, Field(gt=0, le=MAX_WEIGHT_KG, allow_inf_nan=False)]
Percent = Annotated[Decimal, Field(gt=0, le=100, allow_inf_nan=False)]
Price = Annotated[Decimal, Field(gt=0, le=MAX_PRICE_PER_KG, decimal_places=2, allow_inf_nan=False)]
Money = Annotated[Decimal, Field(gt=0, le=MAX_MONEY, decimal_places=2, allow_inf_nan=False)]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


# ---- farmers -------------------------------------------------------------------------------
class FarmerIn(StrictInput):
    name: Text
    phone: Phone
    village: Text
    bank_reference: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
    ) = None


class FarmerUpdate(StrictInput):
    name: Text | None = None
    phone: Phone | None = None
    village: Text | None = None
    bank_reference: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
    ) = None


class FarmerBase(Output):
    id: int
    name: str
    phone: str
    village: str
    bank_reference: str | None


class FarmerOut(FarmerBase):
    outstanding_advance: Decimal  # derived: advances given minus recoveries on finalised payouts


# ---- crops and prices ----------------------------------------------------------------------
class CropIn(StrictInput):
    name: Text
    base_moisture_threshold: Annotated[
        Decimal, Field(ge=0, lt=100, decimal_places=2, allow_inf_nan=False)
    ]
    max_moisture_accepted: Annotated[
        Decimal, Field(gt=0, le=100, decimal_places=2, allow_inf_nan=False)
    ]
    grades: Annotated[list[GradeCode], Field(min_length=1, max_length=10)]


class CropLimitsUpdate(StrictInput):
    base_moisture_threshold: (
        Annotated[Decimal, Field(ge=0, lt=100, decimal_places=2, allow_inf_nan=False)] | None
    ) = None
    max_moisture_accepted: (
        Annotated[Decimal, Field(gt=0, le=100, decimal_places=2, allow_inf_nan=False)] | None
    ) = None


class GradeIn(StrictInput):
    grade: GradeCode


class CropOut(Output):
    id: int
    name: str
    base_moisture_threshold: Decimal
    max_moisture_accepted: Decimal
    grades: list[str]

    @classmethod
    def from_crop(cls, crop) -> "CropOut":
        return cls(
            id=crop.id,
            name=crop.name,
            base_moisture_threshold=crop.base_moisture_threshold,
            max_moisture_accepted=crop.max_moisture_accepted,
            grades=sorted(grade.grade for grade in crop.grades),
        )


class PriceIn(StrictInput):
    crop_id: int = Field(gt=0)
    grade: GradeCode
    price_per_kg: Price
    effective_from: date


class PriceOut(Output):
    id: int
    crop_id: int
    grade: str
    price_per_kg: Decimal
    effective_from: date


# ---- advances ------------------------------------------------------------------------------
class AdvanceIn(StrictInput):
    amount: Money
    given_on: date


class AdvanceOut(Output):
    id: int
    farmer_id: int
    amount: Decimal
    given_on: date


# ---- deliveries ----------------------------------------------------------------------------
class DeliveryDetails(StrictInput):
    grade: GradeCode
    gross_kg: Weight
    moisture: Percent
    delivered_on: date


class DeliveryPreviewIn(DeliveryDetails):
    crop_id: int = Field(gt=0)
    farmer_id: int | None = Field(default=None, gt=0)


class DeliveryIn(DeliveryDetails):
    farmer_id: int = Field(gt=0)
    crop_id: int = Field(gt=0)


class NoteIn(StrictInput):
    kind: DeliveryKind
    amount: Money
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class DeliveryLineOut(Output):
    """A delivery or note as one line of a payout statement."""

    id: int
    farmer_id: int
    crop_id: int
    crop_name: str = Field(validation_alias=AliasPath("crop", "name"))
    grade: str
    kind: DeliveryKind
    delivered_on: date
    gross_kg: Decimal | None
    moisture: Decimal | None
    deduction_pct: Decimal | None
    deduction_kg: Decimal | None
    net_kg: Decimal | None
    applied_price: Decimal | None
    price_list_entry_id: int | None
    amount: Decimal
    payout_id: int | None
    references_delivery_id: int | None
    reason: str | None


class DeliveryOut(DeliveryLineOut):
    payout_status: PayoutStatus | None = Field(
        default=None, validation_alias=AliasPath("payout", "status")
    )


class DeliveryPreviewOut(BaseModel):
    crop_id: int
    crop_name: str
    grade: str
    delivered_on: date
    gross_kg: Decimal
    moisture: Decimal
    moisture_threshold: Decimal
    deduction_pct: Decimal
    deduction_kg: Decimal
    net_kg: Decimal
    applied_price: Decimal
    price_list_entry_id: int
    amount: Decimal


# ---- payouts -------------------------------------------------------------------------------
class PayoutGenerateIn(StrictInput):
    farmer_id: int = Field(gt=0)
    week_start: date


class PayoutOut(Output):
    id: int
    farmer_id: int
    farmer_name: str = Field(validation_alias=AliasPath("farmer", "name"))
    week_start: date
    status: PayoutStatus
    gross_amount: Decimal
    outstanding_before: Decimal
    advance_deduction: Decimal
    net_amount: Decimal
    finalised_at: datetime | None
    paid_at: datetime | None

    @computed_field
    @property
    def week_end(self) -> date:
        return self.week_start + timedelta(days=6)

    @computed_field
    @property
    def recovery_cap(self) -> Decimal:
        """30% of gross: the most that can be recovered this week."""
        return recovery_cap(self.gross_amount)

    @computed_field
    @property
    def outstanding_after(self) -> Decimal:
        """Outstanding advance once this payout is finalised."""
        return self.outstanding_before - self.advance_deduction


class PayoutStatementOut(PayoutOut):
    deliveries: list[DeliveryLineOut]


# ---- ledger --------------------------------------------------------------------------------
class LedgerOut(BaseModel):
    farmer: FarmerBase
    total_advances: Decimal
    total_recovered: Decimal
    outstanding_advance: Decimal
    limit: int
    deliveries_total: int
    advances_total: int
    payouts_total: int
    deliveries: list[DeliveryOut]
    advances: list[AdvanceOut]
    payouts: list[PayoutOut]
