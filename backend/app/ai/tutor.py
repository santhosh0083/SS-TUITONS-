"""The SS Tuitions AI tutor.

TEACHING STANCE
---------------
This tutor guides; it does not hand over answers. A student who receives a
worked solution to their homework has learned nothing and will meet the same
problem again in the exam. The system prompt makes that behaviour explicit, and
the refusal is framed as help rather than obstruction.

PRIVACY
-------
Every student message passes through app/ai/privacy.py before it leaves the
server. No name, email, phone number or student id is ever sent to the AI
provider. On the free tier the provider may train on submitted data, so this is
the boundary that keeps a child's identity out of that.

The student's grade and subject ARE sent, because they are not identifying and
the tutor is useless without them.

LIMITS
------
Each student has a daily message cap. On a shared free-tier quota, one student
working through the night would otherwise leave everyone else with nothing.
"""

import logging
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import privacy
from app.ai.provider import AIError, AINotConfigured, get_provider
from app.core.config import get_settings
from app.models.ai_ml import AIMessage, AISession
from app.models.enums import AISessionMode
from app.models.identity import Student, User

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 12  # keep prompts small; free tiers have tight limits


class TutorError(Exception):
    """Message is safe to show a student."""


class TutorUnavailable(TutorError):
    """AI is not configured. The UI should hide the feature entirely."""


class DailyLimitReached(TutorError):
    pass


def _system_prompt(*, grade: str, subject: str | None) -> str:
    subject_line = f"The student is asking about {subject}." if subject else ""
    return f"""You are a patient tutor for SS Tuitions, an Indian tutoring service.

The student is in Grade {grade}. {subject_line}
They are preparing for Indian examinations: CBSE or Telangana Intermediate
board exams, and possibly JEE, NEET or TG EAPCET.

HOW YOU TEACH — this is the important part:

- Do NOT give the final answer to a homework or practice problem. Guide the
  student to it. This is not you being unhelpful; it is the entire point.
- Start by asking what they have already tried, or what part is confusing.
- Give ONE hint or ONE step at a time, then stop and let them respond.
- When they make a mistake, say where the reasoning went wrong and why, then
  let them retry. Do not simply correct it for them.
- If they are completely stuck after genuinely trying, work through a SIMILAR
  problem with different numbers, then hand the original back to them.
- If they just ask "what is the answer", explain warmly that working it out
  themselves is what makes it stick in the exam, then offer the first step.

CONCEPT QUESTIONS are different. If they ask "what is angular momentum" or
"explain SN1 vs SN2", explain it properly and clearly. Use a concrete example.
Withholding an explanation helps nobody.

STYLE:
- Short paragraphs. Plain English. This student may be 11 years old.
- Use standard notation. Write maths clearly in plain text.
- Be encouraging but never flattering. "That's the right idea, but check the
  sign" beats "Great question!"
- If you are unsure of a fact, say so and suggest they confirm it with their
  tutor. Never state something uncertain as fact.

BOUNDARIES:
- Only discuss school subjects and study skills. If asked about anything else,
  redirect warmly to their studies.
- You have no access to any student's records, marks, or personal details, and
  you must never claim otherwise.
- If a student mentions self-harm, abuse, or being in danger, tell them clearly
  and kindly to speak to a parent, teacher, or a trusted adult immediately, and
  encourage them to contact their SS Tuitions tutor. Do not attempt to counsel
  them yourself."""


async def _messages_today(session: AsyncSession, student_id: uuid.UUID) -> int:
    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=UTC)
    return (
        await session.execute(
            select(func.count())
            .select_from(AIMessage)
            .join(AISession, AISession.id == AIMessage.session_id)
            .where(
                AISession.student_id == student_id,
                AIMessage.role == "user",
                AIMessage.created_at >= today_start,
            )
        )
    ).scalar_one()


async def _student_for_user(session: AsyncSession, user: User) -> Student:
    student = (
        await session.execute(select(Student).where(Student.user_id == user.id))
    ).scalar_one_or_none()
    if student is None:
        raise TutorError("The AI tutor is available to students only.")
    return student


async def start_or_resume_session(
    session: AsyncSession, *, user: User
) -> AISession:
    """Reuse today's open session so a conversation survives a page reload."""
    student = await _student_for_user(session, user)

    existing = (
        await session.execute(
            select(AISession)
            .where(
                AISession.student_id == student.id,
                AISession.mode == AISessionMode.TUTOR,
                AISession.ended_at.is_(None),
            )
            .order_by(AISession.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    created = AISession(
        student_id=student.id,
        mode=AISessionMode.TUTOR,
        started_at=datetime.now(UTC),
        total_tokens_in=0,
        total_tokens_out=0,
    )
    session.add(created)
    await session.flush()
    return created


async def history(
    session: AsyncSession, *, ai_session: AISession
) -> list[dict]:
    rows = (
        await session.execute(
            select(AIMessage)
            .where(AIMessage.session_id == ai_session.id)
            .order_by(AIMessage.created_at)
        )
    ).scalars().all()
    return [
        {"role": m.role, "content": m.content, "at": m.created_at} for m in rows
    ]


async def ask(
    session: AsyncSession,
    *,
    user: User,
    question: str,
    subject: str | None = None,
) -> dict:
    """Send a question to the tutor and store both sides of the exchange."""
    settings = get_settings()

    try:
        provider = get_provider()
    except AINotConfigured as exc:
        raise TutorUnavailable(
            "The AI tutor is not switched on yet. Please ask your tutor."
        ) from exc

    question = question.strip()
    if not question:
        raise TutorError("Please type a question.")
    if len(question) > 2000:
        raise TutorError("That question is too long. Try shortening it.")

    student = await _student_for_user(session, user)

    used = await _messages_today(session, student.id)
    limit = settings.ai_daily_message_limit_per_student
    if used >= limit:
        raise DailyLimitReached(
            f"You have used all {limit} AI tutor questions for today. "
            "It resets tomorrow — and your tutor can help in the meantime."
        )

    ai_session = await start_or_resume_session(session, user=user)

    # ---- Privacy boundary: nothing identifying leaves after this point ----
    if settings.ai_strip_identifiers:
        scrubbed = privacy.scrub_for_student(
            question, full_name=user.full_name, email=user.email
        )
        outgoing = scrubbed.text
        if scrubbed.was_modified:
            logger.info(
                "Removed %d identifier(s) before sending to AI",
                scrubbed.removed_count,
            )
    else:
        outgoing = question

    past = await history(session, ai_session=ai_session)
    recent = past[-MAX_HISTORY_TURNS * 2 :]
    transcript = "\n\n".join(
        f"{'Student' if m['role'] == 'user' else 'Tutor'}: {m['content']}"
        for m in recent
    )
    prompt = (
        f"{transcript}\n\nStudent: {outgoing}" if transcript else outgoing
    )

    try:
        response = await provider.complete(
            system=_system_prompt(grade=student.grade.value, subject=subject),
            prompt=prompt,
            # Generous, because Gemini 3 spends most of this budget on internal
            # reasoning before writing anything: a measured call used 671
            # thinking tokens to produce 148 tokens of answer. At 1200 a longer
            # explanation would be cut off mid-sentence.
            max_tokens=3000,
            temperature=0.6,
        )
    except AIError as exc:
        logger.warning("AI tutor call failed: %s", exc)
        raise TutorError(
            "The AI tutor could not answer just now. Please try again shortly."
        ) from exc

    now = datetime.now(UTC)
    # The student's ORIGINAL text is stored, since the database is ours and the
    # student must be able to read their own conversation back. Only the copy
    # sent to the provider was scrubbed.
    session.add(
        AIMessage(
            session_id=ai_session.id,
            role="user",
            content=question,
            model=response.model,
            tokens_in=response.tokens_in,
            created_at=now,
        )
    )
    session.add(
        AIMessage(
            session_id=ai_session.id,
            role="assistant",
            content=response.text,
            model=response.model,
            tokens_out=response.tokens_out,
            created_at=now,
        )
    )
    ai_session.total_tokens_in += response.tokens_in or 0
    ai_session.total_tokens_out += response.tokens_out or 0
    await session.flush()

    return {
        "answer": response.text,
        "questions_used_today": used + 1,
        "daily_limit": limit,
    }
