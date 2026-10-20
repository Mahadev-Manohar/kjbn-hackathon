from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.api.schemas import CropIn, CropLimitsUpdate, CropOut, GradeIn
from app.persistence import queries
from app.services import master_data

router = APIRouter(prefix="/crops", tags=["crops"])


@router.post("", response_model=CropOut, status_code=status.HTTP_201_CREATED)
def create_crop(body: CropIn, session: DbSession):
    crop = master_data.create_crop(
        session,
        body.name,
        body.base_moisture_threshold,
        body.max_moisture_accepted,
        list(dict.fromkeys(body.grades)),
    )
    return CropOut.from_crop(crop)


@router.get("", response_model=list[CropOut])
def list_crops(session: DbSession):
    return [CropOut.from_crop(crop) for crop in master_data.list_crops(session)]


@router.get("/{crop_id}", response_model=CropOut)
def get_crop(crop_id: int, session: DbSession):
    return CropOut.from_crop(queries.get_crop(session, crop_id))


@router.patch("/{crop_id}", response_model=CropOut)
def update_crop_limits(crop_id: int, body: CropLimitsUpdate, session: DbSession):
    """Change moisture limits for future deliveries; existing deliveries keep their breakdown."""
    crop = master_data.update_crop_limits(
        session, crop_id, body.base_moisture_threshold, body.max_moisture_accepted
    )
    return CropOut.from_crop(crop)


@router.post("/{crop_id}/grades", response_model=CropOut, status_code=status.HTTP_201_CREATED)
def add_grade(crop_id: int, body: GradeIn, session: DbSession):
    return CropOut.from_crop(master_data.add_crop_grade(session, crop_id, body.grade))
