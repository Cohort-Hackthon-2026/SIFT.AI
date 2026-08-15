"""Chat export route (BE2, plan §6 P2/P3).

``POST /api/v1/chats/{chat_id}/export`` renders a chat transcript to PDF / DOCX /
PPTX. Format availability is tier-gated (FREE = PDF only), each export meters an
EXPORT usage event, and the action is written to the audit log. Uses its own
router on the ``/api/v1/chats`` prefix so BE1's chats router stays untouched.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.auth import get_current_user_id
from app.services import entitlements
from app.services.export_service import SUPPORTED_FORMATS, ExportError, export_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chats", tags=["exports"])


class ExportRequest(BaseModel):
    format: str = Field(default="PDF")


@router.post("/{chat_id}/export")
async def export_chat_route(
    request: Request,
    chat_id: str,
    payload: ExportRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> Response:
    fmt = payload.format.upper()
    if fmt not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported format '{payload.format}'. Use one of {sorted(SUPPORTED_FORMATS)}.",
        )

    chat_registry = getattr(request.app.state, "chat_registry", None)
    if chat_registry is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="chat_registry is unavailable.")

    chat = await chat_registry.get_chat(chat_id=chat_id, user_id=current_user_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat '{chat_id}' was not found.")

    # Tier gate: PDF is universal; DOCX needs a paid plan; PPTX needs PRO+.
    profile_registry = getattr(request.app.state, "profile_registry", None)
    chambers_registry = getattr(request.app.state, "chambers_registry", None)
    tier, chambers_id = "FREE", None
    if profile_registry is not None and chambers_registry is not None:
        tier, chambers_id = await entitlements.resolve_effective_tier(
            current_user_id, profile_registry, chambers_registry
        )
    entitlements.enforce_export_format(tier, fmt)

    messages = await chat_registry.list_messages(chat_id=chat_id, user_id=current_user_id)

    # Optional header context: the matter this chat is filed under + chambers.
    matter = None
    matter_id = chat.get("matter_id")
    matter_registry = getattr(request.app.state, "matter_registry", None)
    if matter_id and matter_registry is not None:
        matter = await matter_registry.get_matter(matter_id)
    chambers = None
    if chambers_id and chambers_registry is not None:
        chambers = await chambers_registry.get_chambers(chambers_id)

    try:
        data, filename, mime = export_chat(
            fmt, chat, messages,
            generated_by=current_user_id, matter=matter, chambers=chambers,
        )
    except ExportError as exc:
        # Renderer library unavailable in this deployment.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    # Meter + audit (best-effort — never block the download).
    billing_registry = getattr(request.app.state, "billing_registry", None)
    if billing_registry is not None:
        try:
            await billing_registry.record_usage(current_user_id, "EXPORT", chambers_id=chambers_id)
        except Exception as exc:
            logger.warning("export usage metering failed: %s", exc)
    audit_registry = getattr(request.app.state, "audit_registry", None)
    if audit_registry is not None:
        try:
            await audit_registry.record(
                current_user_id, "CHAT_EXPORT",
                chambers_id=chambers_id, matter_id=matter_id, detail={"format": fmt, "chat_id": chat_id},
            )
        except Exception as exc:
            logger.warning("export audit failed: %s", exc)

    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
