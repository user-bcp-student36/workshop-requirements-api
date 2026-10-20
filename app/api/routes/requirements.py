from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.dependencies import get_requirements_service, require_permissions
from app.schemas import RequirementUploadRead
from app.services.requirements_service import RequirementsService


router = APIRouter(prefix="/requirements", tags=["requirements"])


@router.post(
    "",
    response_model=RequirementUploadRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("requirements:upload"))],
)
async def upload_requirement(
    file: UploadFile = File(...),
    service: RequirementsService = Depends(get_requirements_service),
) -> RequirementUploadRead:
    return await service.save_upload(file)