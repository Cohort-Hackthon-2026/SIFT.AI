"""Privacy / NDPA routes (BE2, plan §6 P1 + P2).

* ``GET /api/v1/privacy/policy-statement`` — public data-handling statement the
  FE can render on the onboarding/settings screen (NDPA 2023 alignment).
* ``POST /api/v1/privacy/delete-my-data`` — the "right to erasure" action: purge
  the caller's documents (Ahnlich vectors + R2 files + registry rows), chats,
  matters, memberships, usage events, audit logs, and profile.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from app.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/privacy", tags=["privacy"])


@router.get("/policy-statement")
async def policy_statement(request: Request) -> dict:
    """Public NDPA data-handling statement. No user data — safe unauthenticated."""
    settings = getattr(request.app.state, "settings", None)
    default_region = getattr(settings, "DEFAULT_DATA_REGION", None) or "NG"
    return {
        "controller": "SIFT.AI",
        "regulation": "Nigeria Data Protection Act (NDPA) 2023",
        "data_region": default_region,
        "data_categories": [
            "Account identity (via Clerk): user id, email, name",
            "Professional profile: role, NBA enrolment number, jurisdiction",
            "Uploaded legal documents and their extracted text",
            "Research chats, queries, and generated analyses",
            "Usage metering for billing",
        ],
        "processing_purposes": [
            "Providing AI-assisted legal research grounded in your documents",
            "Maintaining your chats, matters, and chambers workspace",
            "Billing and plan enforcement",
            "Security, audit, and abuse prevention",
        ],
        "retention": {
            "default_policy": "Documents and chats are retained until you delete "
            "them or invoke erasure. Chambers on Enterprise plans may set a custom "
            "retention window.",
            "erasure_endpoint": "/api/v1/privacy/delete-my-data",
        },
        "data_subject_rights": [
            "Access — GET /api/v1/me/profile and your documents/chats endpoints",
            "Rectification — PUT /api/v1/me/profile",
            "Erasure — POST /api/v1/privacy/delete-my-data",
        ],
        "sub_processors": [
            {"name": "Clerk", "purpose": "Authentication"},
            {"name": "Cloudflare R2", "purpose": "Encrypted document storage"},
            {"name": "Google Gemini", "purpose": "LLM synthesis"},
            {"name": "Neon Postgres", "purpose": "Application database"},
        ],
        "contact": "privacy@sift.ai",
    }


@router.post("/delete-my-data")
async def delete_my_data(
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    """NDPA erasure: irreversibly purge the caller's data across every store."""
    state = request.app.state
    deleted = {
        "documents": 0,
        "chats": 0,
        "matters": 0,
        "memberships": 0,
        "usage_events": 0,
        "audit_logs": 0,
        "profile": False,
    }

    # 1. Documents — purge Ahnlich vectors + R2 objects + registry rows.
    document_registry = getattr(state, "document_registry", None)
    vector_store = getattr(state, "vector_store", None)
    storage = getattr(state, "storage", None)
    if document_registry is not None:
        try:
            docs = await document_registry.list_documents(user_id=current_user_id)
        except Exception as exc:
            logger.error("erasure: list_documents failed: %s", exc)
            docs = []
        for doc in docs:
            doc_id = doc.get("document_id")
            if not doc_id:
                continue
            if vector_store is not None:
                try:
                    await vector_store.delete_document(doc_id)
                except Exception as exc:
                    logger.warning("erasure: vector delete failed for %s: %s", doc_id, exc)
            if storage is not None:
                try:
                    await storage.delete_pdf(doc_id)
                except Exception as exc:
                    logger.warning("erasure: storage delete failed for %s: %s", doc_id, exc)
            try:
                if await document_registry.delete_document(doc_id):
                    deleted["documents"] += 1
            except Exception as exc:
                logger.warning("erasure: registry delete failed for %s: %s", doc_id, exc)

    # 2. Chats (cascades messages).
    chat_registry = getattr(state, "chat_registry", None)
    if chat_registry is not None:
        try:
            chats = await chat_registry.list_chats(user_id=current_user_id)
            for chat in chats:
                if await chat_registry.delete_chat(chat_id=chat["chat_id"], user_id=current_user_id):
                    deleted["chats"] += 1
        except Exception as exc:
            logger.error("erasure: chat purge failed: %s", exc)

    # 3. Matters created by the user.
    matter_registry = getattr(state, "matter_registry", None)
    if matter_registry is not None:
        try:
            removed = await matter_registry.delete_matters_for_user(current_user_id)
            deleted["matters"] = len(removed)
        except Exception as exc:
            logger.error("erasure: matter purge failed: %s", exc)

    # 4. Chambers memberships.
    chambers_registry = getattr(state, "chambers_registry", None)
    if chambers_registry is not None:
        try:
            deleted["memberships"] = await chambers_registry.remove_memberships_for_user(current_user_id)
        except Exception as exc:
            logger.error("erasure: membership purge failed: %s", exc)

    # 5. Usage events.
    billing_registry = getattr(state, "billing_registry", None)
    if billing_registry is not None:
        try:
            deleted["usage_events"] = await billing_registry.delete_usage_for_user(current_user_id)
        except Exception as exc:
            logger.error("erasure: usage purge failed: %s", exc)

    # 6. Audit logs (the user's own trail).
    audit_registry = getattr(state, "audit_registry", None)
    if audit_registry is not None:
        try:
            deleted["audit_logs"] = await audit_registry.delete_logs_for_user(current_user_id)
        except Exception as exc:
            logger.error("erasure: audit purge failed: %s", exc)

    # 7. Profile last.
    profile_registry = getattr(state, "profile_registry", None)
    if profile_registry is not None:
        try:
            deleted["profile"] = await profile_registry.delete_profile(current_user_id)
        except Exception as exc:
            logger.error("erasure: profile delete failed: %s", exc)

    logger.info("NDPA erasure completed for user %s: %s", current_user_id, deleted)
    return {"user_id": current_user_id, "status": "completed", "deleted": deleted}
