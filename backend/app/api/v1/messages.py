"""Messaging endpoints for parents, tutors and admins.

Response models carry display names only. No email or phone number appears in
any response, so a parent and tutor can never obtain each other's contact
details through the platform.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.db.session import get_db
from app.services import messaging
from app.services.messaging import MessagingError, NotAMember

router = APIRouter()
Db = Annotated[AsyncSession, Depends(get_db)]


class Participant(BaseModel):
    id: uuid.UUID
    name: str  # display name only, never contact details


class ConversationSummary(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    student_name: str | None
    subject_line: str | None
    participants: list[Participant]
    last_message_at: datetime | None
    unread_count: int


class MessageOut(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    body: str
    sent_at: datetime
    is_mine: bool


class SendMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    session: Db, user: CurrentUser
) -> list[ConversationSummary]:
    """Conversations you can see.

    Parents see threads about their own children; tutors see threads for
    students they currently teach; admins see all.
    """
    rows = await messaging.list_conversations(session, user=user)
    await session.commit()
    return [ConversationSummary(**r) for r in rows]


@router.get("/unread-count")
async def unread_count(session: Db, user: CurrentUser) -> dict[str, int]:
    return {"unread": await messaging.unread_total(session, user=user)}


@router.get("/{conversation_id}", response_model=list[MessageOut])
async def get_messages(
    conversation_id: uuid.UUID,
    session: Db,
    user: CurrentUser,
    reason: Annotated[
        str | None,
        Query(
            description=(
                "Why an admin is opening this conversation. Recorded in the "
                "audit log. Ignored for participants."
            )
        ),
    ] = None,
) -> list[MessageOut]:
    """Read a conversation.

    When an admin opens a thread they are not a participant in, the access is
    written to the audit log, which a database trigger makes append-only.
    """
    try:
        rows = await messaging.get_messages(
            session, user=user, conversation_id=conversation_id, reason=reason
        )
    except NotAMember as exc:
        # 404 rather than 403: a stranger should not learn the thread exists.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        ) from exc
    await session.commit()
    return [MessageOut(**r) for r in rows]


@router.post(
    "/{conversation_id}", response_model=MessageOut, status_code=status.HTTP_201_CREATED
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    session: Db,
    user: CurrentUser,
) -> MessageOut:
    """Send a message.

    Admins may post as well, so the owner can share a class link directly into
    a parent-tutor thread.
    """
    try:
        created = await messaging.send_message(
            session, user=user, conversation_id=conversation_id, body=payload.body
        )
    except NotAMember as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        ) from exc
    except MessagingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    await session.commit()
    return MessageOut(**created)
