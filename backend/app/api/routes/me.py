"""User profile routes (BE2, plan §6 P1).

``GET /api/v1/me/profile`` returns (and lazily creates) the caller's profile so
the FE onboarding flow always has a row to render. ``PUT`` updates the
onboarding fields. Chambers membership is *not* set here — that goes through the
chambers join/create endpoints so it stays consistent with the memberships
table.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth import get_current_user_id
from app.db.profile_registry import VALID_ROLES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/me", tags=["profile"])


class ProfileResponse(BaseModel):
    user_id: str
    role: str
    nba_number: str | None
    chambers_id: str | None
    default_jurisdiction: str
    onboarded_at: str
    updated_at: str


class UpdateProfileRequest(BaseModel):
    role: str | None = Field(default=None)
    nba_number: str | None = Field(default=None, max_length=64)
    default_jurisdiction: str | None = Field(default=None, max_length=8)


def _registry(request: Request, name: str):
    reg = getattr(request.app.state, name, None)
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{name} is unavailable.",
        )
    return reg


@router.get("/profile", response_model=ProfileResponse)
async def get_my_profile(
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> ProfileResponse:
    profiles = _registry(request, "profile_registry")
    profile = await profiles.get_profile(current_user_id)
    if profile is None:
        # First visit: mint a default profile so onboarding has a row to edit.
        profile = await profiles.upsert_profile(current_user_id)
    return ProfileResponse(**profile)


@router.put("/profile", response_model=ProfileResponse)
async def update_my_profile(
    request: Request,
    payload: UpdateProfileRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> ProfileResponse:
    profiles = _registry(request, "profile_registry")

    if payload.role is not None and payload.role.upper() not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{payload.role}'. Must be one of {sorted(VALID_ROLES)}.",
        )

    profile = await profiles.upsert_profile(
        current_user_id,
        role=payload.role,
        nba_number=payload.nba_number,
        default_jurisdiction=payload.default_jurisdiction,
    )

    audit = getattr(request.app.state, "audit_registry", None)
    if audit is not None:
        changed = {k: v for k, v in payload.model_dump().items() if v is not None}
        try:
            await audit.record(
                current_user_id, "PROFILE_UPDATE",
                chambers_id=profile.get("chambers_id"), detail={"changed": list(changed.keys())},
            )
        except Exception as exc:  # audit is best-effort, never blocks the write
            logger.warning("audit PROFILE_UPDATE failed: %s", exc)

    return ProfileResponse(**profile)
