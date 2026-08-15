"""Unit tests for the entitlements / tier-gating service (BE2)."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services import entitlements as ent


def test_normalize_tier_defaults_and_uppercases() -> None:
    assert ent.normalize_tier(None) == "FREE"
    assert ent.normalize_tier("") == "FREE"
    assert ent.normalize_tier("starter") == "STARTER"
    assert ent.normalize_tier("BOGUS") == "FREE"  # unknown -> default


def test_mode_matrix() -> None:
    assert ent.is_mode_allowed("FREE", "STRICT") is True
    assert ent.is_mode_allowed("FREE", "ENHANCED") is False
    assert ent.is_mode_allowed("STARTER", "ENHANCED") is True
    assert ent.is_mode_allowed("PRO", "enhanced") is True  # case-insensitive


def test_export_format_matrix() -> None:
    assert ent.is_export_format_allowed("FREE", "PDF") is True
    assert ent.is_export_format_allowed("FREE", "DOCX") is False
    assert ent.is_export_format_allowed("STARTER", "DOCX") is True
    assert ent.is_export_format_allowed("STARTER", "PPTX") is False
    assert ent.is_export_format_allowed("PRO", "PPTX") is True


def test_feature_matrix() -> None:
    assert ent.feature_enabled("FREE", "chambers") is False
    assert ent.feature_enabled("STARTER", "chambers") is True
    assert ent.feature_enabled("STARTER", "audit_log") is False
    assert ent.feature_enabled("PRO", "audit_log") is True
    assert ent.feature_enabled("ENTERPRISE", "data_residency") is True


def test_quota_and_remaining() -> None:
    assert ent.quota_for("FREE", "QUERY") == 50
    assert ent.remaining_quota("FREE", "QUERY", used=10) == 40
    assert ent.remaining_quota("FREE", "QUERY", used=999) == 0  # never negative
    # ENTERPRISE is unlimited -> None sentinel.
    assert ent.quota_for("ENTERPRISE", "QUERY") is None
    assert ent.remaining_quota("ENTERPRISE", "QUERY", used=10_000) is None


def test_max_members() -> None:
    assert ent.max_members("FREE") == 1
    assert ent.max_members("STARTER") == 5
    assert ent.max_members("PRO") == 25
    assert ent.max_members("ENTERPRISE") is None


def test_enforce_mode_raises_402_for_free_enhanced() -> None:
    with pytest.raises(HTTPException) as exc:
        ent.enforce_mode("FREE", "ENHANCED")
    assert exc.value.status_code == 402
    assert exc.value.detail["current_tier"] == "FREE"
    assert exc.value.detail["upgrade_required"] == "STARTER"
    # No exception for an allowed mode.
    ent.enforce_mode("FREE", "STRICT")


def test_enforce_export_format_upgrade_targets() -> None:
    with pytest.raises(HTTPException) as docx:
        ent.enforce_export_format("FREE", "DOCX")
    assert docx.value.detail["upgrade_required"] == "STARTER"
    with pytest.raises(HTTPException) as pptx:
        ent.enforce_export_format("STARTER", "PPTX")
    assert pptx.value.detail["upgrade_required"] == "PRO"
    ent.enforce_export_format("PRO", "PPTX")  # allowed -> no raise


def test_enforce_feature_and_quota() -> None:
    with pytest.raises(HTTPException) as feat:
        ent.enforce_feature("FREE", "audit_log")
    assert feat.value.status_code == 402
    with pytest.raises(HTTPException) as quota:
        ent.enforce_quota("FREE", "QUERY", used=50)
    assert quota.value.status_code == 402
    # Under the cap -> no raise; unlimited tier -> never raises.
    ent.enforce_quota("FREE", "QUERY", used=49)
    ent.enforce_quota("ENTERPRISE", "QUERY", used=10_000_000)


class _FakeProfiles:
    def __init__(self, profile):
        self._p = profile

    async def get_profile(self, user_id):
        return self._p


class _FakeChambers:
    def __init__(self, chambers):
        self._c = chambers

    async def get_chambers(self, chambers_id):
        return self._c


async def test_resolve_effective_tier_no_chambers_is_free() -> None:
    tier, chambers_id = await ent.resolve_effective_tier(
        "u1", _FakeProfiles({"chambers_id": None}), _FakeChambers(None)
    )
    assert tier == "FREE"
    assert chambers_id is None


async def test_resolve_effective_tier_reads_chambers_tier() -> None:
    tier, chambers_id = await ent.resolve_effective_tier(
        "u1",
        _FakeProfiles({"chambers_id": "c1"}),
        _FakeChambers({"subscription_tier": "PRO"}),
    )
    assert tier == "PRO"
    assert chambers_id == "c1"


async def test_resolve_effective_tier_degrades_on_registry_error() -> None:
    class _Boom:
        async def get_profile(self, user_id):
            raise RuntimeError("db down")

    tier, chambers_id = await ent.resolve_effective_tier("u1", _Boom(), _FakeChambers(None))
    assert tier == "FREE"
    assert chambers_id is None
