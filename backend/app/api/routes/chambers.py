"""Chambers routes (BE2, plan §6 P2).

A chambers is a team account. The creator becomes its founding PRINCIPAL; others
join with the invite code minted at creation. Team size is gated by the
chambers' subscription tier (FREE = solo, paid tiers add seats). Reading a
chambers or its members requires membership; role changes and removals require
PRINCIPAL. Non-members get 404 so a chambers' existence isn't leaked.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth import get_current_user_id
from app.db.chambers_registry import VALID_MEMBER_ROLES
from app.services import entitlements

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chambers", tags=["chambers"])


class CreateChambersRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class JoinChambersRequest(BaseModel):
    invite_code: str = Field(min_length=1, max_length=32)


class UpdateMemberRequest(BaseModel):
    role: str = Field(min_length=1, max_length=16)


def _registry(request: Request, name: str):
    reg = getattr(request.app.state, name, None)
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{name} is unavailable.",
        )
    return reg


async def _require_membership(request: Request, chambers_id: str, user_id: str) -> dict:
    chambers_registry = _registry(request, "chambers_registry")
    membership = await chambers_registry.get_membership(chambers_id, user_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chambers '{chambers_id}' was not found.")
    return membership


async def _sync_profile_chambers(request: Request, user_id: str, chambers_id: str | None) -> None:
    profiles = getattr(request.app.state, "profile_registry", None)
    if profiles is None:
        return
    try:
        await profiles.upsert_profile(user_id, chambers_id=chambers_id, _chambers_explicit=True)
    except Exception as exc:
        logger.warning("profile chambers sync failed: %s", exc)


async def _audit(request: Request, user_id: str, action: str, **kw) -> None:
    audit = getattr(request.app.state, "audit_registry", None)
    if audit is None:
        return
    try:
        await audit.record(user_id, action, **kw)
    except Exception as exc:
        logger.warning("audit %s failed: %s", action, exc)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_chambers(
    request: Request,
    payload: CreateChambersRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    chambers_registry = _registry(request, "chambers_registry")
    chambers = await chambers_registry.create_chambers(payload.name, current_user_id)
    await _sync_profile_chambers(request, current_user_id, chambers["chambers_id"])
    await _audit(
        request, current_user_id, "CHAMBERS_CREATE",
        chambers_id=chambers["chambers_id"], detail={"name": chambers["name"]},
    )
    return chambers


@router.get("")
async def list_my_chambers(
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    chambers_registry = _registry(request, "chambers_registry")
    rows = await chambers_registry.list_chambers_for_user(current_user_id)
    # Attach the caller's role in each.
    out = []
    for chambers in rows:
        membership = await chambers_registry.get_membership(chambers["chambers_id"], current_user_id)
        out.append({**chambers, "my_role": membership["role"] if membership else None})
    return {"chambers": out}


@router.post("/join")
async def join_chambers(
    request: Request,
    payload: JoinChambersRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    chambers_registry = _registry(request, "chambers_registry")
    chambers = await chambers_registry.get_chambers_by_invite(payload.invite_code.strip().upper())
    if chambers is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite code.")

    existing = await chambers_registry.get_membership(chambers["chambers_id"], current_user_id)
    if existing is None:
        # Enforce the tier's seat limit before adding a new member.
        members = await chambers_registry.list_members(chambers["chambers_id"])
        limit = entitlements.max_members(chambers.get("subscription_tier"))
        if limit is not None and len(members) >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "message": f"This chambers has reached its {limit}-member limit for the "
                    f"{entitlements.normalize_tier(chambers.get('subscription_tier'))} plan.",
                    "current_tier": entitlements.normalize_tier(chambers.get("subscription_tier")),
                    "upgrade_required": "STARTER",
                },
            )

    membership = await chambers_registry.add_member(chambers["chambers_id"], current_user_id, role="ASSOCIATE")
    await _sync_profile_chambers(request, current_user_id, chambers["chambers_id"])
    await _audit(request, current_user_id, "CHAMBERS_JOIN", chambers_id=chambers["chambers_id"])
    return {"chambers": chambers, "membership": membership}


@router.get("/{chambers_id}")
async def get_chambers(
    request: Request,
    chambers_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    membership = await _require_membership(request, chambers_id, current_user_id)
    chambers_registry = _registry(request, "chambers_registry")
    chambers = await chambers_registry.get_chambers(chambers_id)
    if chambers is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chambers '{chambers_id}' was not found.")
    members = await chambers_registry.list_members(chambers_id)
    # Only elevated roles get to see the invite code.
    result = {**chambers, "my_role": membership["role"], "members": members}
    if membership["role"] not in {"PRINCIPAL", "PARTNER"}:
        result.pop("invite_code", None)
    return result


@router.get("/{chambers_id}/members")
async def list_members(
    request: Request,
    chambers_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    await _require_membership(request, chambers_id, current_user_id)
    chambers_registry = _registry(request, "chambers_registry")
    return {"members": await chambers_registry.list_members(chambers_id)}


@router.patch("/{chambers_id}/members/{member_user_id}")
async def update_member_role(
    request: Request,
    chambers_id: str,
    member_user_id: str,
    payload: UpdateMemberRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    membership = await _require_membership(request, chambers_id, current_user_id)
    if membership["role"] != "PRINCIPAL":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a chambers principal can change member roles.",
        )
    if payload.role.upper() not in VALID_MEMBER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of {sorted(VALID_MEMBER_ROLES)}.",
        )
    chambers_registry = _registry(request, "chambers_registry")
    target = await chambers_registry.get_membership(chambers_id, member_user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this chambers.")
    updated = await chambers_registry.add_member(chambers_id, member_user_id, role=payload.role)
    await _audit(
        request, current_user_id, "CHAMBERS_ROLE_CHANGE",
        chambers_id=chambers_id, detail={"member": member_user_id, "role": payload.role.upper()},
    )
    return updated


@router.delete("/{chambers_id}/members/{member_user_id}")
async def remove_member(
    request: Request,
    chambers_id: str,
    member_user_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    membership = await _require_membership(request, chambers_id, current_user_id)
    # A principal may remove anyone; a member may remove themselves (leave).
    if membership["role"] != "PRINCIPAL" and member_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a chambers principal can remove other members.",
        )
    chambers_registry = _registry(request, "chambers_registry")
    target = await chambers_registry.get_membership(chambers_id, member_user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this chambers.")

    await chambers_registry.remove_member(chambers_id, member_user_id)
    # If the removed user's profile pointed here, clear it.
    await _sync_profile_chambers(request, member_user_id, None)
    await _audit(
        request, current_user_id, "CHAMBERS_REMOVE_MEMBER",
        chambers_id=chambers_id, detail={"member": member_user_id},
    )
    return {"chambers_id": chambers_id, "removed_user_id": member_user_id, "removed": True}
