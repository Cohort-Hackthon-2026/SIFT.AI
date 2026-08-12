"""Audit-log read route (BE2, plan §6 P3).

``GET /api/v1/audit`` returns a chambers' compliance trail. It is gated three
ways: the chambers' plan must include the ``audit_log`` feature (PRO+), the
caller must be a PRINCIPAL/PARTNER of that chambers, and the log is always
scoped to that one chambers. Writes happen everywhere via ``audit_registry``;
this is the only reader.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth import get_current_user_id
from app.services import entitlements

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

_ELEVATED = {"PRINCIPAL", "PARTNER"}


def _registry(request: Request, name: str):
    reg = getattr(request.app.state, name, None)
    if reg is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"{name} is unavailable.")
    return reg


@router.get("")
async def list_audit_log(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    profiles = _registry(request, "profile_registry")
    chambers_registry = _registry(request, "chambers_registry")
    audit_registry = _registry(request, "audit_registry")

    tier, chambers_id = await entitlements.resolve_effective_tier(current_user_id, profiles, chambers_registry)
    if not chambers_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The audit log is a chambers feature. Create or join a chambers first.",
        )

    # Plan gate (402 if the tier doesn't include the audit-log feature).
    entitlements.enforce_feature(tier, "audit_log")

    # Role gate: only chambers leadership reads the firm-wide trail.
    membership = await chambers_registry.get_membership(chambers_id, current_user_id)
    if membership is None or membership["role"] not in _ELEVATED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a chambers principal or partner can read the audit log.",
        )

    logs = await audit_registry.list_logs(chambers_id=chambers_id, limit=limit)
    return {"chambers_id": chambers_id, "tier": tier, "count": len(logs), "logs": logs}
