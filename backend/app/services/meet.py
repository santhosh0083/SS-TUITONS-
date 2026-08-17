"""Google Meet integration for scheduled classes.

Uses the Google Calendar API with `conferenceDataVersion=1`, which creates a
genuine Meet conference attached to a calendar event. This is the supported
path for *scheduled* classes with a known attendee list; the Meet REST API's
spaces endpoint is aimed at ad-hoc meetings and does not attach to an event.

ONE MEETING PER CLASS SESSION
-----------------------------
Every ClassSession gets its own event and therefore its own Meet link. There is
no shared link, and no link is ever reused across students.

NO FAKE LINKS, EVER
-------------------
If Google is not configured, this module raises. It never invents a URL, never
returns a placeholder, and never falls back to a generic room. The database
enforces the same rule independently: `ck_class_sessions_no_url_when_unconfigured`
rejects any row carrying a meeting_url while integration_status is
'not_configured'. Application and database would both have to be wrong for a
fake link to reach a parent.

REQUIREMENTS
------------
Google Workspace. A free @gmail.com account cannot create Meet conferences
through the API. Set in .env:

    GOOGLE_INTEGRATION_ENABLED=true
    GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_WORKSPACE_DOMAIN

ACCESS CONTROL
--------------
The Meet URL is never public. It is returned only to the assigned tutor, the
enrolled student, and that student's linked parents, resolved through the
visibility layer on every request.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


class MeetError(Exception):
    """Meet operation failed. Message is safe to show an admin."""


class MeetNotConfigured(MeetError):
    """Google is not set up. Classes are still created, without a link."""


@dataclass(frozen=True)
class CreatedMeeting:
    meeting_url: str
    google_event_id: str
    google_conference_id: str | None


def is_configured() -> bool:
    """True when a Meet link can actually be created.

    Used to decide whether the admin UI offers meeting creation, rather than
    letting someone click a button that cannot work.
    """
    s = get_settings()
    return bool(
        s.google_integration_enabled
        and s.google_client_id
        and s.google_client_secret
    )


def configuration_hint() -> str:
    """Why Meet is unavailable, phrased for the owner rather than a developer."""
    s = get_settings()
    if not s.google_integration_enabled:
        return (
            "Google Meet is not connected yet. It needs a Google Workspace "
            "account — a free Gmail account cannot create Meet links "
            "automatically. Classes can still be scheduled; add the link "
            "manually for now."
        )
    if not (s.google_client_id and s.google_client_secret):
        return (
            "Google Workspace is enabled but the client credentials are "
            "missing. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
        )
    return "Google Meet is connected."


async def create_meeting_for_class(
    *,
    access_token: str,
    summary: str,
    description: str,
    start: datetime,
    end: datetime,
    timezone: str,
    attendee_emails: list[str],
) -> CreatedMeeting:
    """Create a calendar event with a dedicated Meet conference.

    `attendee_emails` are the accounts permitted to join. Attendees are added
    so Google can enforce entry, but SS Tuitions does not rely on that alone:
    the link is only ever surfaced to authorised users by the API.
    """
    if not is_configured():
        raise MeetNotConfigured(configuration_hint())

    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": timezone},
        "end": {"dateTime": end.isoformat(), "timeZone": timezone},
        "attendees": [{"email": e} for e in attendee_emails],
        "conferenceData": {
            "createRequest": {
                # Must be unique per request; Google uses it to deduplicate
                # retries, so a network retry cannot create a second meeting.
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
        "guestsCanInviteOthers": False,
        "guestsCanSeeOtherGuests": False,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                CALENDAR_EVENTS_URL,
                params={"conferenceDataVersion": 1, "sendUpdates": "none"},
                headers={"Authorization": f"Bearer {access_token}"},
                json=body,
            )
    except httpx.HTTPError as exc:
        raise MeetError(
            f"Could not reach Google Calendar: {type(exc).__name__}"
        ) from exc

    if response.status_code == 401:
        raise MeetError("Google authorisation has expired. Reconnect the account.")
    if response.status_code == 403:
        raise MeetError(
            "Google refused the request. This usually means the account is not "
            "a Workspace account, or the Calendar API is not enabled."
        )
    if response.status_code >= 400:
        logger.error(
            "Calendar API error %s: %s", response.status_code, response.text[:300]
        )
        raise MeetError(f"Google Calendar returned HTTP {response.status_code}")

    data = response.json()
    conference = data.get("conferenceData", {})
    entry_points = conference.get("entryPoints", [])
    video = next(
        (e for e in entry_points if e.get("entryPointType") == "video"), None
    )

    if not video or not video.get("uri"):
        # Google accepted the event but produced no conference. Rather than
        # store an event with no way in, fail loudly.
        raise MeetError(
            "Google created the event but did not return a Meet link. The "
            "account may not be licensed for Meet."
        )

    return CreatedMeeting(
        meeting_url=video["uri"],
        google_event_id=data["id"],
        google_conference_id=conference.get("conferenceId"),
    )


async def delete_meeting(*, access_token: str, google_event_id: str) -> None:
    """Cancel the calendar event when a class is cancelled.

    Failure is logged rather than raised: a stale calendar entry is a smaller
    problem than blocking the admin from cancelling the class.
    """
    if not is_configured():
        return
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.delete(
                f"{CALENDAR_EVENTS_URL}/{google_event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"sendUpdates": "none"},
            )
    except httpx.HTTPError:
        logger.warning(
            "Could not delete Google event %s; it may need removing by hand",
            google_event_id,
        )
