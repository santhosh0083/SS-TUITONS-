"""Private parent-tutor messaging with admin oversight.

WHO MAY SEE WHAT
----------------
  Parent  only conversations about their own children
  Tutor   only conversations about students in batches they currently teach
  Admin   every conversation, and every access is written to the audit log

Membership is re-checked from live database state on every request, not stored
once and trusted. Revoking a tutor's assignment removes their access to those
conversations immediately.

CONTACT DETAILS NEVER CROSS
---------------------------
A parent sees the tutor's display name. A tutor sees the parent's display name.
Neither response schema carries an email or phone number — those fields never
leave the server, so there is nothing to leak in the browser's network tab.

ENCRYPTION
----------
Bodies are encrypted with AES-256-GCM before storage. The server holds the key
and can decrypt, deliberately, so the owner can review conversations for child
safety. This is NOT end-to-end encryption; see docs/PRIVACY_MODEL.md.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academics import BatchStudent, TutorAssignment
from app.models.enums import (
    ConversationType,
    EnrolmentStatus,
    NotificationType,
    RoleCode,
)
from app.models.identity import Parent, Student, StudentParent, Tutor, User
from app.models.messaging import (
    Conversation,
    ConversationMember,
    Message,
    Notification,
)
from app.services import audit, crypto


class MessagingError(Exception):
    """Message is safe to show the user."""


class NotAMember(MessagingError):
    """Caller may not see this conversation."""


# ---------------------------------------------------------------------------
# Authorisation
# ---------------------------------------------------------------------------


async def _tutor_teaches_student(
    session: AsyncSession, *, tutor_user_id: uuid.UUID, student_id: uuid.UUID
) -> bool:
    found = (
        await session.execute(
            select(BatchStudent.student_id)
            .join(TutorAssignment, TutorAssignment.batch_id == BatchStudent.batch_id)
            .join(Tutor, Tutor.id == TutorAssignment.tutor_id)
            .where(
                Tutor.user_id == tutor_user_id,
                BatchStudent.student_id == student_id,
                TutorAssignment.revoked_on.is_(None),
                BatchStudent.status == EnrolmentStatus.ACTIVE,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return found is not None


async def _parent_of_student(
    session: AsyncSession, *, parent_user_id: uuid.UUID, student_id: uuid.UUID
) -> bool:
    found = (
        await session.execute(
            select(StudentParent.student_id)
            .join(Parent, Parent.id == StudentParent.parent_id)
            .where(
                Parent.user_id == parent_user_id,
                StudentParent.student_id == student_id,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return found is not None


async def assert_can_access(
    session: AsyncSession,
    *,
    user: User,
    conversation: Conversation,
    reason: str | None = None,
) -> bool:
    """Raise unless `user` may read this conversation.

    Returns True when access was granted as an admin, so the caller knows an
    audit entry is required. Admin access is legitimate but must never be
    silent.
    """
    roles = user.role_codes

    if user.is_superadmin or RoleCode.ADMIN in roles:
        await audit.record(
            session,
            action="conversation.admin_viewed",
            entity_type="conversation",
            entity_id=conversation.id,
            actor_user_id=user.id,
            after={"student_id": str(conversation.student_id), "reason": reason},
        )
        return True

    if RoleCode.TUTOR in roles and await _tutor_teaches_student(
        session, tutor_user_id=user.id, student_id=conversation.student_id
    ):
        return False

    if RoleCode.PARENT in roles and await _parent_of_student(
        session, parent_user_id=user.id, student_id=conversation.student_id
    ):
        return False

    raise NotAMember("You do not have access to this conversation")


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


async def get_or_create_conversation(
    session: AsyncSession,
    *,
    student_id: uuid.UUID,
    tutor_id: uuid.UUID,
    subject_line: str | None = None,
) -> Conversation:
    """One conversation per (student, tutor) pair.

    Created when a tutor is assigned, so the thread already exists before
    anyone needs it. Members are the student's parents plus the tutor.
    """
    tutor = (
        await session.execute(select(Tutor).where(Tutor.id == tutor_id))
    ).scalar_one_or_none()
    if tutor is None:
        raise MessagingError("That tutor no longer exists")

    existing = (
        await session.execute(
            select(Conversation)
            .join(
                ConversationMember,
                ConversationMember.conversation_id == Conversation.id,
            )
            .where(
                Conversation.student_id == student_id,
                ConversationMember.user_id == tutor.user_id,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    conversation = Conversation(
        conversation_type=ConversationType.PARENT_TUTOR,
        student_id=student_id,
        subject_line=subject_line,
        is_archived=False,
    )
    session.add(conversation)
    await session.flush()

    session.add(ConversationMember(conversation_id=conversation.id, user_id=tutor.user_id))

    parent_user_ids = (
        await session.execute(
            select(Parent.user_id)
            .join(StudentParent, StudentParent.parent_id == Parent.id)
            .where(StudentParent.student_id == student_id)
        )
    ).scalars().all()
    for parent_user_id in parent_user_ids:
        session.add(
            ConversationMember(conversation_id=conversation.id, user_id=parent_user_id)
        )

    await session.flush()
    return conversation


async def list_conversations(
    session: AsyncSession, *, user: User
) -> list[dict]:
    """Conversations visible to this user, newest activity first.

    Deliberately returns display names only — no contact details for anyone.
    """
    roles = user.role_codes
    is_admin = user.is_superadmin or RoleCode.ADMIN in roles

    stmt = select(Conversation).where(Conversation.is_archived.is_(False))

    if not is_admin:
        # Restrict to conversations this user is a member of. Membership is
        # verified again per-conversation on open.
        stmt = stmt.join(
            ConversationMember,
            ConversationMember.conversation_id == Conversation.id,
        ).where(ConversationMember.user_id == user.id)

    stmt = stmt.order_by(
        Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc()
    )
    conversations = (await session.execute(stmt)).scalars().unique().all()

    out: list[dict] = []
    for conv in conversations:
        student_name = (
            await session.execute(
                select(User.full_name)
                .join(Student, Student.user_id == User.id)
                .where(Student.id == conv.student_id)
            )
        ).scalar_one_or_none()

        # Everyone in the thread except the caller, by display name only.
        others = (
            await session.execute(
                select(User.id, User.full_name)
                .join(ConversationMember, ConversationMember.user_id == User.id)
                .where(
                    ConversationMember.conversation_id == conv.id,
                    User.id != user.id,
                )
            )
        ).all()

        last_read = (
            await session.execute(
                select(ConversationMember.last_read_at).where(
                    ConversationMember.conversation_id == conv.id,
                    ConversationMember.user_id == user.id,
                )
            )
        ).scalar_one_or_none()

        unread_stmt = select(func.count()).select_from(Message).where(
            Message.conversation_id == conv.id,
            Message.sender_user_id != user.id,
            Message.deleted_at.is_(None),
        )
        if last_read is not None:
            unread_stmt = unread_stmt.where(Message.sent_at > last_read)
        unread = (await session.execute(unread_stmt)).scalar_one()

        out.append(
            {
                "id": conv.id,
                "student_id": conv.student_id,
                "student_name": student_name,
                "subject_line": conv.subject_line,
                "participants": [{"id": r.id, "name": r.full_name} for r in others],
                "last_message_at": conv.last_message_at,
                "unread_count": unread,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


async def get_messages(
    session: AsyncSession,
    *,
    user: User,
    conversation_id: uuid.UUID,
    reason: str | None = None,
) -> list[dict]:
    conversation = (
        await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise NotAMember("You do not have access to this conversation")

    viewed_as_admin = await assert_can_access(
        session, user=user, conversation=conversation, reason=reason
    )

    rows = (
        await session.execute(
            select(Message, User.full_name)
            .join(User, User.id == Message.sender_user_id)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
            .order_by(Message.sent_at)
        )
    ).all()

    out: list[dict] = []
    for message, sender_name in rows:
        try:
            body = crypto.decrypt(message.body, conversation_id=str(conversation_id))
        except crypto.EncryptionError:
            # A message we cannot decrypt must not break the whole thread.
            body = "[This message could not be decrypted]"
        out.append(
            {
                "id": message.id,
                "sender_id": message.sender_user_id,
                "sender_name": sender_name,
                "body": body,
                "sent_at": message.sent_at,
                "is_mine": message.sender_user_id == user.id,
                "viewed_as_admin": viewed_as_admin,
            }
        )

    # Mark read for members; an admin reading does not clear anyone's unread.
    if not viewed_as_admin:
        member = (
            await session.execute(
                select(ConversationMember).where(
                    ConversationMember.conversation_id == conversation_id,
                    ConversationMember.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if member is not None:
            member.last_read_at = datetime.now(UTC)

    return out


async def send_message(
    session: AsyncSession,
    *,
    user: User,
    conversation_id: uuid.UUID,
    body: str,
) -> dict:
    """Post a message. Admins may post too, so the owner can share a class link
    directly into the thread."""
    body = body.strip()
    if not body:
        raise MessagingError("Message cannot be empty")
    if len(body) > 5000:
        raise MessagingError("Message is too long (5000 characters maximum)")

    conversation = (
        await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise NotAMember("You do not have access to this conversation")

    posted_as_admin = await assert_can_access(
        session, user=user, conversation=conversation, reason="posting a message"
    )

    now = datetime.now(UTC)
    message = Message(
        conversation_id=conversation_id,
        sender_user_id=user.id,
        body=crypto.encrypt(body, conversation_id=str(conversation_id)),
        sent_at=now,
    )
    session.add(message)
    conversation.last_message_at = now
    await session.flush()

    # Notify everyone else in the thread.
    recipients = (
        await session.execute(
            select(ConversationMember.user_id).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id != user.id,
            )
        )
    ).scalars().all()

    for recipient_id in recipients:
        session.add(
            Notification(
                user_id=recipient_id,
                notification_type=NotificationType.MESSAGE_RECEIVED,
                title=f"New message from {user.full_name}",
                # The preview deliberately omits the message body: notifications
                # are stored unencrypted, and copying the text here would undo
                # the encryption applied to the message itself.
                body=None,
                link_url=f"/messages/{conversation_id}",
                related_entity_type="conversation",
                related_entity_id=conversation_id,
                is_read=False,
                sent_at=now,
            )
        )

    if posted_as_admin:
        await audit.record(
            session,
            action="conversation.admin_posted",
            entity_type="conversation",
            entity_id=conversation_id,
            actor_user_id=user.id,
        )

    return {
        "id": message.id,
        "sender_id": user.id,
        "sender_name": user.full_name,
        "body": body,
        "sent_at": now,
        "is_mine": True,
    }


async def unread_total(session: AsyncSession, *, user: User) -> int:
    """Unread count across all this user's conversations, for the nav badge."""
    member_rows = (
        await session.execute(
            select(
                ConversationMember.conversation_id, ConversationMember.last_read_at
            ).where(ConversationMember.user_id == user.id)
        )
    ).all()

    total = 0
    for conversation_id, last_read in member_rows:
        stmt = select(func.count()).select_from(Message).where(
            Message.conversation_id == conversation_id,
            Message.sender_user_id != user.id,
            Message.deleted_at.is_(None),
        )
        if last_read is not None:
            stmt = stmt.where(Message.sent_at > last_read)
        total += (await session.execute(stmt)).scalar_one()
    return total
