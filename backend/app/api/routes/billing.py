"""Billing + usage routes (BE2, plan §6 P3).

Billing is **per-chambers**, not per-seat: a chambers carries one subscription
tier, and every member inherits its entitlements. Pricing is a flat monthly fee
per tier (usage overage is metered via ``usage_events`` for future overage
billing).

* ``GET  /api/v1/billing/plan``     — current tier, entitlements, usage-vs-quota.
* ``POST /api/v1/billing/checkout`` — start a Paystack transaction to upgrade.
* ``POST /api/v1/billing/webhook``  — Paystack callback (signature-verified, no
  auth header) that actually flips the chambers' tier once payment succeeds.

Paystack is optional: when ``PAYSTACK_SECRET_KEY`` is unset the checkout returns
a ``provider: "mock"`` stub so the FE and tests can exercise the flow, and the
webhook rejects unverifiable calls. Amounts are in **kobo** (Paystack's unit;
₦1 = 100 kobo).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth import get_current_user_id
from app.services import entitlements

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"

# Flat monthly price per tier, in kobo. ENTERPRISE is sales-led (no self-serve
# checkout). FREE needs no payment. These are the public prices the FE renders.
PLAN_CATALOG: dict[str, dict] = {
    "FREE": {"amount_kobo": 0, "currency": "NGN", "self_serve": False,
             "label": "Free", "blurb": "Solo practice — Strict mode, PDF export."},
    "STARTER": {"amount_kobo": 1_500_000, "currency": "NGN", "self_serve": True,
                "label": "Starter", "blurb": "Small chambers — Enhanced mode, DOCX export, up to 5 members."},
    "PRO": {"amount_kobo": 6_000_000, "currency": "NGN", "self_serve": True,
            "label": "Pro", "blurb": "Growing firm — PPTX export, audit log, up to 25 members."},
    "ENTERPRISE": {"amount_kobo": None, "currency": "NGN", "self_serve": False,
                   "label": "Enterprise", "blurb": "Data residency, custom retention, unlimited members. Contact sales."},
}


class CheckoutRequest(BaseModel):
    tier: str = Field(min_length=1, max_length=16)
    chambers_id: str | None = Field(default=None)
    email: str | None = Field(default=None, max_length=255)
    callback_url: str | None = Field(default=None, max_length=1024)


def _registry(request: Request, name: str):
    reg = getattr(request.app.state, name, None)
    if reg is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"{name} is unavailable.")
    return reg


def _paystack_secret() -> str | None:
    # Read at call time (not import) so tests can monkeypatch, matching auth.py.
    return os.getenv("PAYSTACK_SECRET_KEY") or None


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def _audit(request: Request, user_id: str, action: str, **kw) -> None:
    audit = getattr(request.app.state, "audit_registry", None)
    if audit is None:
        return
    try:
        await audit.record(user_id, action, **kw)
    except Exception as exc:  # best-effort
        logger.warning("audit %s failed: %s", action, exc)


@router.get("/plan")
async def get_plan(
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    """Current tier, its entitlements, and this month's usage against quota."""
    profiles = _registry(request, "profile_registry")
    chambers_registry = _registry(request, "chambers_registry")
    billing = _registry(request, "billing_registry")

    tier, chambers_id = await entitlements.resolve_effective_tier(current_user_id, profiles, chambers_registry)
    ent = entitlements.get_entitlements(tier)

    # Usage is chambers-wide when the user is in a chambers, else personal.
    since = _month_start()
    if chambers_id:
        used = await billing.usage_summary(chambers_id=chambers_id, since=since)
    else:
        used = await billing.usage_summary(user_id=current_user_id, since=since)

    quotas = {}
    for event_type, limit in ent["quotas"].items():
        consumed = used.get(event_type, 0)
        quotas[event_type] = {
            "used": consumed,
            "limit": limit,  # None = unlimited
            "remaining": entitlements.remaining_quota(tier, event_type, consumed),
        }

    return {
        "tier": tier,
        "chambers_id": chambers_id,
        "entitlements": ent,
        "usage": {"period_start": since.isoformat(), "quotas": quotas},
        "plans": PLAN_CATALOG,
    }


@router.post("/checkout")
async def checkout(
    request: Request,
    payload: CheckoutRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    """Start a Paystack transaction to upgrade a chambers to a paid tier.

    Only a chambers PRINCIPAL may pay (billing is per-chambers). Returns the
    ``authorization_url`` the FE redirects to. Falls back to a mock reference
    when Paystack isn't configured so the flow is exercisable end to end.
    """
    tier = payload.tier.upper()
    plan = PLAN_CATALOG.get(tier)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown tier '{payload.tier}'. Must be one of {sorted(PLAN_CATALOG)}.",
        )
    if not plan["self_serve"] or plan["amount_kobo"] in (None, 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The {plan['label']} plan is not available for self-serve checkout. "
            f"{'Contact sales.' if tier == 'ENTERPRISE' else 'It is free.'}",
        )

    # Resolve which chambers is being billed and confirm the caller runs it.
    profiles = _registry(request, "profile_registry")
    chambers_registry = _registry(request, "chambers_registry")
    chambers_id = payload.chambers_id
    if not chambers_id:
        profile = await profiles.get_profile(current_user_id)
        chambers_id = (profile or {}).get("chambers_id")
    if not chambers_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create or join a chambers before subscribing — billing is per-chambers.",
        )
    membership = await chambers_registry.get_membership(chambers_id, current_user_id)
    if membership is None:
        # Don't leak the chambers' existence to non-members.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chambers not found.")
    if membership["role"] != "PRINCIPAL":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a chambers principal can manage billing.",
        )

    amount_kobo = plan["amount_kobo"]
    reference = f"sift_{uuid4().hex}"
    metadata = {"chambers_id": chambers_id, "tier": tier, "user_id": current_user_id}

    secret = _paystack_secret()
    if not secret:
        # Degraded mode: no Paystack configured. Hand back a mock reference so
        # the FE can still drive the UI and integration tests can run.
        logger.warning("PAYSTACK_SECRET_KEY not set — returning mock checkout for %s", reference)
        await _audit(request, current_user_id, "BILLING_CHECKOUT_INIT",
                     chambers_id=chambers_id, detail={"tier": tier, "reference": reference, "provider": "mock"})
        return {
            "provider": "mock",
            "reference": reference,
            "tier": tier,
            "amount_kobo": amount_kobo,
            "currency": plan["currency"],
            "authorization_url": None,
            "message": "Paystack is not configured; this is a mock checkout for development.",
        }

    email = payload.email
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An email is required to start checkout.",
        )

    import httpx

    body = {
        "email": email,
        "amount": amount_kobo,
        "currency": plan["currency"],
        "reference": reference,
        "metadata": metadata,
    }
    if payload.callback_url:
        body["callback_url"] = payload.callback_url

    try:
        async with httpx.AsyncClient(timeout=20.0) as http:
            resp = await http.post(
                PAYSTACK_INIT_URL,
                json=body,
                headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.error("Paystack initialize failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the payment provider. Please try again.",
        ) from exc

    auth = (data or {}).get("data", {})
    await _audit(request, current_user_id, "BILLING_CHECKOUT_INIT",
                 chambers_id=chambers_id, detail={"tier": tier, "reference": reference, "provider": "paystack"})
    return {
        "provider": "paystack",
        "reference": auth.get("reference", reference),
        "tier": tier,
        "amount_kobo": amount_kobo,
        "currency": plan["currency"],
        "authorization_url": auth.get("authorization_url"),
        "access_code": auth.get("access_code"),
    }


@router.post("/webhook")
async def paystack_webhook(request: Request) -> dict:
    """Paystack webhook: verified by HMAC-SHA512 signature, not an auth header.

    On ``charge.success`` we read the ``chambers_id`` + ``tier`` we stamped into
    the transaction metadata at checkout, flip the chambers' tier, and record a
    subscription row. Always returns 200 for verified events so Paystack stops
    retrying; rejects unverifiable calls with 401.
    """
    secret = _paystack_secret()
    raw = await request.body()

    if not secret:
        # Can't verify without the secret — refuse rather than trust the payload.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Billing webhook is not configured.")

    signature = request.headers.get("x-paystack-signature", "")
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature.")

    try:
        event = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed webhook body.")

    event_type = event.get("event")
    data = event.get("data", {}) or {}
    if event_type != "charge.success":
        # Acknowledge everything else so Paystack doesn't retry.
        return {"status": "ignored", "event": event_type}

    metadata = data.get("metadata", {}) or {}
    chambers_id = metadata.get("chambers_id")
    tier = (metadata.get("tier") or "").upper()
    reference = data.get("reference")
    if not chambers_id or tier not in entitlements.ENTITLEMENTS:
        logger.error("webhook charge.success missing/invalid metadata: %s", metadata)
        return {"status": "ignored", "reason": "missing chambers_id/tier"}

    chambers_registry = getattr(request.app.state, "chambers_registry", None)
    billing = getattr(request.app.state, "billing_registry", None)
    if chambers_registry is not None:
        await chambers_registry.set_tier(chambers_id, tier)
    if billing is not None:
        await billing.create_subscription(
            chambers_id=chambers_id, tier=tier, status="ACTIVE",
            period_start=datetime.now(timezone.utc), external_ref=reference,
        )

    audit = getattr(request.app.state, "audit_registry", None)
    if audit is not None:
        try:
            await audit.record(
                metadata.get("user_id", "system"), "BILLING_UPGRADE",
                chambers_id=chambers_id, detail={"tier": tier, "reference": reference},
            )
        except Exception as exc:
            logger.warning("audit BILLING_UPGRADE failed: %s", exc)

    logger.info("Chambers %s upgraded to %s (ref %s)", chambers_id, tier, reference)
    return {"status": "ok", "chambers_id": chambers_id, "tier": tier}
