from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.dependencies import get_requirements_service, require_roles
from app.schemas.requirements import RequirementUploadResponse
from app.security import Identity
from app.services.requirements_service import RequirementsService


router = APIRouter(prefix="/api", tags=["requirements"])


@router.post(
    "/requirements",
    response_model=RequirementUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_requirement(
    file: UploadFile = File(...),
    _: Identity = Depends(require_roles("user", "admin")),
    service: RequirementsService = Depends(get_requirements_service),
) -> RequirementUploadResponse:
    # Se lee en memoria con límite configurado para evitar escrituras parciales inseguras.
    content = await file.read(service.max_bytes + 1)
    return service.save_upload(file=file, content=content)