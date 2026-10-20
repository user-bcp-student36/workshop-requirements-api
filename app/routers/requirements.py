from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.dependencies import get_current_principal, get_requirement_service
from app.schemas import Principal, RequirementResponse
from app.services import RequirementService

router = APIRouter(prefix="/api", tags=["requirements"])


@router.get("/requirements", response_model=list[RequirementResponse])
def list_requirements(
    principal: Principal = Depends(get_current_principal),
    service: RequirementService = Depends(get_requirement_service),
) -> list[RequirementResponse]:
    return service.list_requirements(principal)


@router.post(
    "/requirements",
    response_model=RequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_requirement(
    file: UploadFile = File(...),
    principal: Principal = Depends(get_current_principal),
    service: RequirementService = Depends(get_requirement_service),
) -> RequirementResponse:
    return await service.store_requirement(file, principal)