"""DORA Art. 28 Register of Information routes (consume ``core.thirdparty``).

Read-only listing/concentration/export for any authenticated reader; registering
providers, functions, and contractual arrangements requires effective-admin.
Console over :func:`core.thirdparty.get_register`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth.types import AuthUser
from core.thirdparty import (
    ContractualArrangement,
    DataSensitivity,
    FunctionCriticality,
    ICTFunction,
    ICTProvider,
    ProviderType,
    RegisterValidationError,
    ServiceAssessment,
    Substitutability,
    get_register,
)

from ._guards import admin_principal, read_guard

router = APIRouter(prefix="/thirdparty", tags=["compliance:thirdparty"])


class ProviderRequest(BaseModel):
    """Register or update an ICT third-party provider."""

    name: str = Field(..., min_length=1, max_length=300)
    id: Optional[str] = None
    lei: Optional[str] = None
    provider_type: ProviderType = ProviderType.LEGAL_ENTITY
    country: Optional[str] = None
    is_critical_designated: bool = False
    parent_id: Optional[str] = None


class FunctionRequest(BaseModel):
    """Register or update a supported business function."""

    name: str = Field(..., min_length=1, max_length=300)
    id: Optional[str] = None
    criticality: FunctionCriticality = FunctionCriticality.NOT_CRITICAL
    reasons_for_criticality: str = ""


class AssessmentModel(BaseModel):
    """Art. 28(8) arrangement assessment."""

    supports_critical_function: bool = False
    substitutability: Substitutability = Substitutability.EASILY_SUBSTITUTABLE
    exit_plan_exists: bool = False
    processes_personal_data: bool = False
    data_sensitivity: DataSensitivity = DataSensitivity.NONE


class ArrangementRequest(BaseModel):
    """Register or update a contractual arrangement (keyed by reference number)."""

    reference_number: str = Field(..., min_length=1, max_length=200)
    provider_id: str = Field(..., min_length=1)
    function_ids: List[str] = Field(default_factory=list)
    ict_service_type: str = ""
    subcontractor_ids: List[str] = Field(default_factory=list)
    annual_cost: Optional[float] = None
    assessment: AssessmentModel = Field(default_factory=AssessmentModel)


@router.get("/providers", dependencies=[Depends(read_guard)])
async def list_providers() -> Dict[str, Any]:
    """List registered ICT third-party providers."""
    providers = await get_register().list_providers()
    return {"providers": [p.to_dict() for p in providers]}


@router.get("/functions", dependencies=[Depends(read_guard)])
async def list_functions() -> Dict[str, Any]:
    """List registered business functions."""
    functions = await get_register().list_functions()
    return {"functions": [f.to_dict() for f in functions]}


@router.get("/arrangements", dependencies=[Depends(read_guard)])
async def list_arrangements() -> Dict[str, Any]:
    """List registered contractual arrangements."""
    arrangements = await get_register().list_arrangements()
    return {"arrangements": [a.to_dict() for a in arrangements]}


@router.get("/concentration", dependencies=[Depends(read_guard)])
async def concentration() -> Dict[str, Any]:
    """Third-party concentration view (Art. 29 single-point-of-failure)."""
    return await get_register().concentration_summary()


@router.get("/export", dependencies=[Depends(read_guard)])
async def export_register() -> Dict[str, Any]:
    """Render the register in the ESA ITS template layout."""
    return await get_register().export_register()


@router.post("/providers", status_code=201)
async def register_provider(
    body: ProviderRequest, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Insert or update an ICT third-party provider."""
    provider = ICTProvider(
        name=body.name,
        lei=body.lei,
        provider_type=body.provider_type,
        country=body.country,
        is_critical_designated=body.is_critical_designated,
        parent_id=body.parent_id,
        **({"id": body.id} if body.id else {}),
    )
    try:
        saved = await get_register().register_provider(provider)
    except RegisterValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return saved.to_dict()


@router.post("/functions", status_code=201)
async def register_function(
    body: FunctionRequest, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Insert or update a supported business function."""
    function = ICTFunction(
        name=body.name,
        criticality=body.criticality,
        reasons_for_criticality=body.reasons_for_criticality,
        **({"id": body.id} if body.id else {}),
    )
    saved = await get_register().register_function(function)
    return saved.to_dict()


@router.post("/arrangements", status_code=201)
async def register_arrangement(
    body: ArrangementRequest, _: AuthUser = Depends(admin_principal)
) -> Dict[str, Any]:
    """Insert or update a contractual arrangement (validates referenced entities)."""
    arrangement = ContractualArrangement(
        reference_number=body.reference_number,
        provider_id=body.provider_id,
        function_ids=body.function_ids,
        ict_service_type=body.ict_service_type,
        subcontractor_ids=body.subcontractor_ids,
        annual_cost=body.annual_cost,
        assessment=ServiceAssessment(
            supports_critical_function=body.assessment.supports_critical_function,
            substitutability=body.assessment.substitutability,
            exit_plan_exists=body.assessment.exit_plan_exists,
            processes_personal_data=body.assessment.processes_personal_data,
            data_sensitivity=body.assessment.data_sensitivity,
        ),
    )
    try:
        saved = await get_register().register_arrangement(arrangement)
    except RegisterValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return saved.to_dict()


__all__ = ["router"]
