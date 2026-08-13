"""Matter routes (BE2, plan §6 P2).

A matter is a case workspace. Documents and chats can be filed under a matter
via ``matter_id``. Visibility is role-aware:

* the creator always sees their own matters;
* PRINCIPAL/PARTNER members see every matter in their chambers;
* ASSOCIATE/TRAINEE members see the ones they created.

Editing/archiving requires being the creator or a PRINCIPAL/PARTNER of the
matter's chambers. Cross-account access returns 404 (never 403) so a matter's
existence isn't leaked.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth import get_current_user_id
from app.db.matter_registry import VALID_MATTER_STATUS, VALID_PRACTICE_AREAS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/matters", tags=["matters"])

_ELEVATED = {"PRINCIPAL", "PARTNER"}


class CreateMatterRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    client_name: str | None = Field(default=None, max_length=512)
    practice_area: str = Field(default="OTHER")
    jurisdiction: str = Field(default="NG", max_length=8)
    chambers_id: str | None = Field(default=None)


class UpdateMatterRequest(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    client_name: str | None = Field(default=None, max_length=512)
    practice_area: str | None = Field(default=None)
    jurisdiction: str | None = Field(default=None, max_length=8)
    status: str | None = Field(default=None)


class AttachDocumentsRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)


class AttachChatsRequest(BaseModel):
    chat_ids: list[str] = Field(default_factory=list)


def _registry(request: Request, name: str):
    reg = getattr(request.app.state, name, None)
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{name} is unavailable.",
        )
    return reg


async def _membership_role(request: Request, chambers_id: str | None, user_id: str) -> str | None:
    """Return the caller's role in ``chambers_id`` (or None if not a member / no chambers)."""
    if not chambers_id:
        return None
    chambers_registry = getattr(request.app.state, "chambers_registry", None)
    if chambers_registry is None:
        return None
    membership = await chambers_registry.get_membership(chambers_id, user_id)
    return membership["role"] if membership else None


async def _load_visible_matter(request: Request, matter_id: str, user_id: str) -> tuple[dict, str | None]:
    """Fetch a matter the caller may view, or raise 404. Returns (matter, role)."""
    matters = _registry(request, "matter_registry")
    matter = await matters.get_matter(matter_id)
    if matter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Matter '{matter_id}' was not found.")
    if matter["created_by_user_id"] == user_id:
        return matter, "OWNER"
    role = await _membership_role(request, matter.get("chambers_id"), user_id)
    if role is None:
        # Not the creator and not a chambers member → pretend it doesn't exist.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Matter '{matter_id}' was not found.")
    return matter, role


def _can_edit(role: str | None) -> bool:
    return role == "OWNER" or role in _ELEVATED


async def _audit(request: Request, user_id: str, action: str, **kw) -> None:
    audit = getattr(request.app.state, "audit_registry", None)
    if audit is None:
        return
    try:
        await audit.record(user_id, action, **kw)
    except Exception as exc:  # best-effort
        logger.warning("audit %s failed: %s", action, exc)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_matter(
    request: Request,
    payload: CreateMatterRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    matters = _registry(request, "matter_registry")

    if payload.practice_area.upper() not in VALID_PRACTICE_AREAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid practice_area. Must be one of {sorted(VALID_PRACTICE_AREAS)}.",
        )

    # Filing under a chambers requires membership in it.
    if payload.chambers_id:
        role = await _membership_role(request, payload.chambers_id, current_user_id)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of that chambers.",
            )

    matter = await matters.create_matter(
        created_by_user_id=current_user_id,
        title=payload.title,
        client_name=payload.client_name,
        practice_area=payload.practice_area,
        jurisdiction=payload.jurisdiction,
        chambers_id=payload.chambers_id,
    )
    await _audit(
        request, current_user_id, "MATTER_CREATE",
        chambers_id=payload.chambers_id, matter_id=matter["matter_id"],
        detail={"title": matter["title"]},
    )
    return matter


@router.get("")
async def list_matters(
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    matters = _registry(request, "matter_registry")
    visible: dict[str, dict] = {m["matter_id"]: m for m in await matters.list_by_creator(current_user_id)}

    chambers_registry = getattr(request.app.state, "chambers_registry", None)
    if chambers_registry is not None:
        try:
            for chambers in await chambers_registry.list_chambers_for_user(current_user_id):
                membership = await chambers_registry.get_membership(chambers["chambers_id"], current_user_id)
                if membership and membership["role"] in _ELEVATED:
                    for m in await matters.list_by_chambers(chambers["chambers_id"]):
                        visible[m["matter_id"]] = m
        except Exception as exc:
            logger.warning("list_matters chambers expansion failed: %s", exc)

    ordered = sorted(visible.values(), key=lambda m: m["created_at"], reverse=True)
    return {"matters": ordered}


@router.get("/{matter_id}")
async def get_matter_workspace(
    request: Request,
    matter_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    matter, _role = await _load_visible_matter(request, matter_id, current_user_id)

    documents: list[dict] = []
    chats: list[dict] = []
    document_registry = getattr(request.app.state, "document_registry", None)
    if document_registry is not None:
        # Documents are the shared artifacts of the matter workspace.
        documents = await document_registry.list_documents_by_matter(matter_id)
    chat_registry = getattr(request.app.state, "chat_registry", None)
    if chat_registry is not None:
        # Chats are personal research threads — only the caller's own.
        chats = await chat_registry.list_chats_by_matter(matter_id, user_id=current_user_id)

    return {"matter": matter, "documents": documents, "chats": chats}


@router.patch("/{matter_id}")
async def update_matter(
    request: Request,
    matter_id: str,
    payload: UpdateMatterRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    matters = _registry(request, "matter_registry")
    matter, role = await _load_visible_matter(request, matter_id, current_user_id)
    if not _can_edit(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the matter owner or a chambers principal/partner can edit it.",
        )

    if payload.practice_area is not None and payload.practice_area.upper() not in VALID_PRACTICE_AREAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid practice_area. Must be one of {sorted(VALID_PRACTICE_AREAS)}.",
        )
    if payload.status is not None and payload.status.upper() not in VALID_MATTER_STATUS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Must be one of {sorted(VALID_MATTER_STATUS)}.",
        )

    updated = await matters.update_matter(
        matter_id,
        title=payload.title,
        client_name=payload.client_name,
        practice_area=payload.practice_area,
        jurisdiction=payload.jurisdiction,
        status=payload.status,
    )
    await _audit(
        request, current_user_id, "MATTER_UPDATE",
        chambers_id=matter.get("chambers_id"), matter_id=matter_id,
        detail={"changed": [k for k, v in payload.model_dump().items() if v is not None]},
    )
    return updated


@router.delete("/{matter_id}")
async def archive_matter(
    request: Request,
    matter_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    """Archive a matter (reversible). Its documents/chats keep their association
    so the workspace can be restored; nothing is destroyed."""
    matters = _registry(request, "matter_registry")
    matter, role = await _load_visible_matter(request, matter_id, current_user_id)
    if not _can_edit(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the matter owner or a chambers principal/partner can archive it.",
        )

    updated = await matters.update_matter(matter_id, status="ARCHIVED")

    document_count = 0
    chat_count = 0
    document_registry = getattr(request.app.state, "document_registry", None)
    if document_registry is not None:
        document_count = len(await document_registry.list_documents_by_matter(matter_id))
    chat_registry = getattr(request.app.state, "chat_registry", None)
    if chat_registry is not None:
        chat_count = len(await chat_registry.list_chats_by_matter(matter_id))

    await _audit(
        request, current_user_id, "MATTER_ARCHIVE",
        chambers_id=matter.get("chambers_id"), matter_id=matter_id,
        detail={"documents": document_count, "chats": chat_count},
    )
    return {
        "matter_id": matter_id,
        "status": "ARCHIVED",
        "matter": updated,
        "archived_documents": document_count,
        "archived_chats": chat_count,
    }


@router.post("/{matter_id}/documents")
async def attach_documents(
    request: Request,
    matter_id: str,
    payload: AttachDocumentsRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    await _load_visible_matter(request, matter_id, current_user_id)
    document_registry = _registry(request, "document_registry")

    attached: list[str] = []
    skipped: list[str] = []
    for document_id in payload.document_ids:
        result = await document_registry.set_document_matter(document_id, current_user_id, matter_id)
        (attached if result else skipped).append(document_id)

    await _audit(
        request, current_user_id, "MATTER_ATTACH_DOCS",
        matter_id=matter_id, detail={"attached": attached, "skipped": skipped},
    )
    return {"matter_id": matter_id, "attached": attached, "skipped": skipped}


@router.delete("/{matter_id}/documents/{document_id}")
async def detach_document(
    request: Request,
    matter_id: str,
    document_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    await _load_visible_matter(request, matter_id, current_user_id)
    document_registry = _registry(request, "document_registry")
    result = await document_registry.set_document_matter(document_id, current_user_id, None)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document '{document_id}' was not found.")
    return {"matter_id": matter_id, "document_id": document_id, "detached": True}


@router.post("/{matter_id}/chats")
async def attach_chats(
    request: Request,
    matter_id: str,
    payload: AttachChatsRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    await _load_visible_matter(request, matter_id, current_user_id)
    chat_registry = _registry(request, "chat_registry")

    attached: list[str] = []
    skipped: list[str] = []
    for chat_id in payload.chat_ids:
        result = await chat_registry.set_chat_matter(chat_id, current_user_id, matter_id)
        (attached if result else skipped).append(chat_id)

    await _audit(
        request, current_user_id, "MATTER_ATTACH_CHATS",
        matter_id=matter_id, detail={"attached": attached, "skipped": skipped},
    )
    return {"matter_id": matter_id, "attached": attached, "skipped": skipped}


@router.delete("/{matter_id}/chats/{chat_id}")
async def detach_chat(
    request: Request,
    matter_id: str,
    chat_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    await _load_visible_matter(request, matter_id, current_user_id)
    chat_registry = _registry(request, "chat_registry")
    result = await chat_registry.set_chat_matter(chat_id, current_user_id, None)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat '{chat_id}' was not found.")
    return {"matter_id": matter_id, "chat_id": chat_id, "detached": True}
