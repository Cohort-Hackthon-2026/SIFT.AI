"""Tests for /api/v1/billing (BE2): plan/usage, Paystack checkout, signed webhook."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json

from app.main import app


def _run(coro):
    return asyncio.run(coro)


def _set_tier(chambers_id: str, tier: str) -> None:
    _run(app.state.chambers_registry.set_tier(chambers_id, tier))


# ---------------------------------------------------------------- GET /plan

def test_get_plan_free_user_shape(client) -> None:
    body = client.get("/api/v1/billing/plan").json()
    assert body["tier"] == "FREE"
    assert body["chambers_id"] is None
    assert "quotas" in body["entitlements"]
    # Usage block reports this month's consumption against each quota.
    query_quota = body["usage"]["quotas"]["QUERY"]
    assert query_quota["limit"] == 50
    assert query_quota["used"] == 0
    assert query_quota["remaining"] == 50
    # The public price list is echoed for the pricing page.
    assert body["plans"]["STARTER"]["amount_kobo"] == 1_500_000
    assert body["plans"]["PRO"]["self_serve"] is True
    assert body["plans"]["ENTERPRISE"]["amount_kobo"] is None


def test_get_plan_reflects_chambers_tier(client) -> None:
    cid = client.post("/api/v1/chambers", json={"name": "Plan Chambers"}).json()["chambers_id"]
    _set_tier(cid, "PRO")
    body = client.get("/api/v1/billing/plan").json()
    assert body["tier"] == "PRO"
    assert body["chambers_id"] == cid


def test_get_plan_requires_auth(raw_client) -> None:
    assert raw_client.get("/api/v1/billing/plan").status_code == 401


# ---------------------------------------------------------------- checkout

def test_checkout_mock_when_paystack_unconfigured(client, as_user, monkeypatch) -> None:
    monkeypatch.delenv("PAYSTACK_SECRET_KEY", raising=False)
    as_user("principal-a")
    client.post("/api/v1/chambers", json={"name": "Checkout Chambers"})
    res = client.post("/api/v1/billing/checkout", json={"tier": "STARTER"})
    assert res.status_code == 200
    body = res.json()
    assert body["provider"] == "mock"
    assert body["tier"] == "STARTER"
    assert body["amount_kobo"] == 1_500_000
    assert body["reference"].startswith("sift_")


def test_checkout_requires_a_chambers(client, monkeypatch) -> None:
    monkeypatch.delenv("PAYSTACK_SECRET_KEY", raising=False)
    # No chambers on the caller's profile -> 400 (billing is per-chambers).
    res = client.post("/api/v1/billing/checkout", json={"tier": "STARTER"})
    assert res.status_code == 400


def test_checkout_only_principal_may_pay(client, as_user, monkeypatch) -> None:
    monkeypatch.delenv("PAYSTACK_SECRET_KEY", raising=False)
    as_user("owner-b")
    created = client.post("/api/v1/chambers", json={"name": "Pay Chambers"}).json()
    cid, invite = created["chambers_id"], created["invite_code"]
    _set_tier(cid, "STARTER")

    as_user("assoc-b")
    client.post("/api/v1/chambers/join", json={"invite_code": invite})
    res = client.post("/api/v1/billing/checkout", json={"tier": "PRO", "chambers_id": cid})
    assert res.status_code == 403


def test_checkout_enterprise_is_sales_led_400(client, as_user, monkeypatch) -> None:
    monkeypatch.delenv("PAYSTACK_SECRET_KEY", raising=False)
    as_user("principal-c")
    client.post("/api/v1/chambers", json={"name": "Ent Chambers"})
    res = client.post("/api/v1/billing/checkout", json={"tier": "ENTERPRISE"})
    assert res.status_code == 400


def test_checkout_unknown_tier_422(client, as_user, monkeypatch) -> None:
    monkeypatch.delenv("PAYSTACK_SECRET_KEY", raising=False)
    as_user("principal-d")
    client.post("/api/v1/chambers", json={"name": "Bad Tier Chambers"})
    res = client.post("/api/v1/billing/checkout", json={"tier": "PLATINUM"})
    assert res.status_code == 422


def test_checkout_requires_auth(raw_client) -> None:
    assert raw_client.post("/api/v1/billing/checkout", json={"tier": "STARTER"}).status_code == 401


# ---------------------------------------------------------------- webhook

def _sign(secret: str, raw: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha512).hexdigest()


def test_webhook_success_upgrades_chambers(client, raw_client, as_user, monkeypatch) -> None:
    secret = "sk_test_webhook"
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", secret)

    as_user("webhook-principal")
    cid = client.post("/api/v1/chambers", json={"name": "Webhook Chambers"}).json()["chambers_id"]

    event = {
        "event": "charge.success",
        "data": {
            "reference": "sift_abc123",
            "metadata": {"chambers_id": cid, "tier": "PRO", "user_id": "webhook-principal"},
        },
    }
    raw = json.dumps(event).encode("utf-8")
    # Webhook takes no auth header — verified purely by the signature.
    res = raw_client.post(
        "/api/v1/billing/webhook",
        content=raw,
        headers={"x-paystack-signature": _sign(secret, raw), "Content-Type": "application/json"},
    )
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "chambers_id": cid, "tier": "PRO"}

    # The chambers' tier really flipped.
    as_user("webhook-principal")
    assert client.get("/api/v1/billing/plan").json()["tier"] == "PRO"


def test_webhook_rejects_bad_signature(raw_client, monkeypatch) -> None:
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", "sk_test_webhook")
    raw = json.dumps({"event": "charge.success", "data": {}}).encode("utf-8")
    res = raw_client.post(
        "/api/v1/billing/webhook",
        content=raw,
        headers={"x-paystack-signature": "deadbeef", "Content-Type": "application/json"},
    )
    assert res.status_code == 401


def test_webhook_503_when_unconfigured(raw_client, monkeypatch) -> None:
    monkeypatch.delenv("PAYSTACK_SECRET_KEY", raising=False)
    res = raw_client.post("/api/v1/billing/webhook", content=b"{}")
    assert res.status_code == 503


def test_webhook_ignores_non_charge_events(raw_client, monkeypatch) -> None:
    secret = "sk_test_webhook"
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", secret)
    raw = json.dumps({"event": "transfer.success", "data": {}}).encode("utf-8")
    res = raw_client.post(
        "/api/v1/billing/webhook",
        content=raw,
        headers={"x-paystack-signature": _sign(secret, raw)},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"
