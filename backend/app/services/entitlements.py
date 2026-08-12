"""Entitlements / tier-gating service (BE2, plan §6 P3).

Single source of truth for "what can this tier do". The effective tier for a
user is their chambers' ``subscription_tier`` (or FREE if they have no chambers).
Routes call the ``enforce_*`` helpers, which raise HTTP 402 when a tier is out of
its lane; BE1's chat route calls :func:`resolve_effective_tier` +
:func:`enforce_mode` to keep Enhanced mode behind a paid plan.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

# Ordered low -> high so callers can compare "at least" if needed later.
TIER_ORDER = ["FREE", "STARTER", "PRO", "ENTERPRISE"]

# ``None`` in a quota slot means unlimited. Numbers are per calendar month.
ENTITLEMENTS: dict[str, dict[str, Any]] = {
    "FREE": {
        "allowed_modes": ["STRICT"],
        "quotas": {"QUERY": 50, "DOC_UPLOAD": 20, "EXPORT": 5, "AUDIO_MIN": 30},
        "export_formats": ["PDF"],
        "features": {"chambers": False, "audit_log": False, "data_residency": False},
        "max_members": 1,
    },
    "STARTER": {
        "allowed_modes": ["STRICT", "ENHANCED"],
        "quotas": {"QUERY": 500, "DOC_UPLOAD": 200, "EXPORT": 100, "AUDIO_MIN": 300},
        "export_formats": ["PDF", "DOCX"],
        "features": {"chambers": True, "audit_log": False, "data_residency": False},
        "max_members": 5,
    },
    "PRO": {
        "allowed_modes": ["STRICT", "ENHANCED"],
        "quotas": {"QUERY": 5000, "DOC_UPLOAD": 2000, "EXPORT": 1000, "AUDIO_MIN": 3000},
        "export_formats": ["PDF", "DOCX", "PPTX"],
        "features": {"chambers": True, "audit_log": True, "data_residency": False},
        "max_members": 25,
    },
    "ENTERPRISE": {
        "allowed_modes": ["STRICT", "ENHANCED"],
        "quotas": {"QUERY": None, "DOC_UPLOAD": None, "EXPORT": None, "AUDIO_MIN": None},
        "export_formats": ["PDF", "DOCX", "PPTX"],
        "features": {"chambers": True, "audit_log": True, "data_residency": True},
        "max_members": None,
    },
}

DEFAULT_TIER = "FREE"


def normalize_tier(tier: str | None) -> str:
    if not tier:
        return DEFAULT_TIER
    upper = tier.upper()
    return upper if upper in ENTITLEMENTS else DEFAULT_TIER


def get_entitlements(tier: str | None) -> dict[str, Any]:
    return ENTITLEMENTS[normalize_tier(tier)]


def is_mode_allowed(tier: str | None, mode: str) -> bool:
    return (mode or "").upper() in get_entitlements(tier)["allowed_modes"]


def quota_for(tier: str | None, event_type: str) -> int | None:
    return get_entitlements(tier)["quotas"].get((event_type or "").upper())


def remaining_quota(tier: str | None, event_type: str, used: int) -> int | None:
    limit = quota_for(tier, event_type)
    if limit is None:
        return None  # unlimited
    return max(0, limit - used)


def is_export_format_allowed(tier: str | None, fmt: str) -> bool:
    return (fmt or "").upper() in get_entitlements(tier)["export_formats"]


def feature_enabled(tier: str | None, feature: str) -> bool:
    return bool(get_entitlements(tier)["features"].get(feature, False))


def max_members(tier: str | None) -> int | None:
    return get_entitlements(tier)["max_members"]


# --------------------------------------------------------------------------- #
# Enforcement — raise HTTP 402 (Payment Required) so the FE can route to the
# upgrade screen, distinct from 401 (auth) / 403 (ownership).
# --------------------------------------------------------------------------- #

def _upgrade(detail: str, tier: str, needed: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={"message": detail, "current_tier": normalize_tier(tier), "upgrade_required": needed},
    )


def enforce_mode(tier: str | None, mode: str) -> None:
    if not is_mode_allowed(tier, mode):
        raise _upgrade(
            f"{(mode or '').upper()} mode requires a paid plan.",
            tier or DEFAULT_TIER,
            needed="STARTER",
        )


def enforce_export_format(tier: str | None, fmt: str) -> None:
    if not is_export_format_allowed(tier, fmt):
        raise _upgrade(
            f"{(fmt or '').upper()} export is not available on your plan.",
            tier or DEFAULT_TIER,
            needed="PRO" if (fmt or "").upper() == "PPTX" else "STARTER",
        )


def enforce_feature(tier: str | None, feature: str) -> None:
    if not feature_enabled(tier, feature):
        raise _upgrade(
            f"The '{feature}' feature is not available on your plan.",
            tier or DEFAULT_TIER,
            needed="PRO" if feature in {"audit_log"} else "STARTER",
        )


def enforce_quota(tier: str | None, event_type: str, used: int) -> None:
    limit = quota_for(tier, event_type)
    if limit is not None and used >= limit:
        raise _upgrade(
            f"You have reached your monthly {(event_type or '').upper()} limit ({limit}).",
            tier or DEFAULT_TIER,
            needed="STARTER",
        )


async def resolve_effective_tier(
    user_id: str,
    profile_registry: Any,
    chambers_registry: Any,
) -> tuple[str, str | None]:
    """Resolve (tier, chambers_id) for a user.

    Individual users with no chambers are FREE. This is the one call BE1's chat
    route needs before :func:`enforce_mode`. Never raises — degrades to
    (FREE, None) if the registries are unavailable.
    """
    try:
        profile = await profile_registry.get_profile(user_id)
    except Exception:
        profile = None
    chambers_id = (profile or {}).get("chambers_id")
    if not chambers_id:
        return DEFAULT_TIER, None
    try:
        chambers = await chambers_registry.get_chambers(chambers_id)
    except Exception:
        chambers = None
    if not chambers:
        return DEFAULT_TIER, chambers_id
    return normalize_tier(chambers.get("subscription_tier")), chambers_id
