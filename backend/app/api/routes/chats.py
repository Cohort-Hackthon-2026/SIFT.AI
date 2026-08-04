from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chats", tags=["chats"])


class CreateChatRequest(BaseModel):
    title: str = Field(default="New Research Chat", max_length=255)
    mode: str = Field(default="STRICT")
    document_ids: list[str] = Field(default_factory=list)


class UpdateChatRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    mode: str | None = Field(default=None)
    document_ids: list[str] | None = Field(default=None)


class ChatResponse(BaseModel):
    chat_id: str
    user_id: str
    title: str
    mode: str
    document_ids: list[str]
    created_at: str
    updated_at: str


class ChatListResponse(BaseModel):
    chats: list[ChatResponse]


class MessageResponse(BaseModel):
    message_id: str
    chat_id: str
    role: str
    content: str
    metadata: dict[str, Any]
    created_at: str


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]


class ChatDeleteResponse(BaseModel):
    chat_id: str
    deleted: bool


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    request: Request,
    payload: CreateChatRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> ChatResponse:
    """Create a new chat research session bound to optional document_ids."""
    chat_registry = getattr(request.app.state, "chat_registry", None)
    if not chat_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat registry service is unavailable.",
        )

    record = await chat_registry.create_chat(
        user_id=current_user_id,
        title=payload.title,
        mode=payload.mode,
        document_ids=payload.document_ids,
    )
    return ChatResponse(**record)


@router.get("", response_model=ChatListResponse)
async def list_chats(
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
) -> ChatListResponse:
    """List all chat sessions owned by the authenticated user."""
    chat_registry = getattr(request.app.state, "chat_registry", None)
    if not chat_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat registry service is unavailable.",
        )

    records = await chat_registry.list_chats(user_id=current_user_id)
    return ChatListResponse(chats=[ChatResponse(**rec) for rec in records])


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    request: Request,
    chat_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> ChatResponse:
    """Get metadata for a specific chat session."""
    chat_registry = getattr(request.app.state, "chat_registry", None)
    if not chat_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat registry service is unavailable.",
        )

    chat = await chat_registry.get_chat(chat_id=chat_id, user_id=current_user_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat '{chat_id}' was not found.",
        )
    return ChatResponse(**chat)


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    request: Request,
    chat_id: str,
    payload: UpdateChatRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> ChatResponse:
    """Update title, mode, or bound document_ids for a chat session."""
    chat_registry = getattr(request.app.state, "chat_registry", None)
    if not chat_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat registry service is unavailable.",
        )

    updated = await chat_registry.update_chat(
        chat_id=chat_id,
        user_id=current_user_id,
        title=payload.title,
        mode=payload.mode,
        document_ids=payload.document_ids,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat '{chat_id}' was not found.",
        )
    return ChatResponse(**updated)


@router.delete("/{chat_id}", response_model=ChatDeleteResponse)
async def delete_chat(
    request: Request,
    chat_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> ChatDeleteResponse:
    """Delete a chat session and purge all its messages."""
    chat_registry = getattr(request.app.state, "chat_registry", None)
    if not chat_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat registry service is unavailable.",
        )

    deleted = await chat_registry.delete_chat(chat_id=chat_id, user_id=current_user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat '{chat_id}' was not found.",
        )
    return ChatDeleteResponse(chat_id=chat_id, deleted=True)


@router.get("/{chat_id}/messages", response_model=MessageListResponse)
async def list_chat_messages(
    request: Request,
    chat_id: str,
    current_user_id: str = Depends(get_current_user_id),
) -> MessageListResponse:
    """Retrieve full chronological message history for a chat session."""
    chat_registry = getattr(request.app.state, "chat_registry", None)
    if not chat_registry:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat registry service is unavailable.",
        )

    # First check chat ownership
    chat = await chat_registry.get_chat(chat_id=chat_id, user_id=current_user_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat '{chat_id}' was not found.",
        )

    messages = await chat_registry.list_messages(chat_id=chat_id, user_id=current_user_id)
    return MessageListResponse(messages=[MessageResponse(**m) for m in messages])
