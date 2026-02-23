"""Availability service — spec §6.1 CheckAvailability backend logic."""
import logging
import uuid
from datetime import datetime
from typing import Any

import pytz
from sqlalchemy.orm import Session

from app.models.event import Event, EventStatus, ConstraintLevel
from app.models.attendee import EventAttendee
from app.models.user import User

logger = logging.getLogger(__name__)


def check_availability(
    db: Session,
    user_ids: list[uuid.UUID],
    range_start_utc: datetime,
    range_end_utc: datetime,
) -> dict[str, Any]:
    """Return busy blocks, DND conflicts, and constraint flags for users in a time range.

    Per spec §6.1:
    - busy_blocks: existing events
    - constraint_flags: Hard vs Soft
    - dnd_conflicts: DND window overlaps
    """
    result: dict[str, Any] = {
        "busy_blocks": [],
        "dnd_conflicts": [],
        "users_checked": [str(uid) for uid in user_ids],
    }

    for uid in user_ids:
        user = db.query(User).filter(User.user_id == uid).first()
        if not user:
            continue

        # Fetch existing events for this user in the range
        events = (
            db.query(Event)
            .join(EventAttendee)
            .filter(
                EventAttendee.user_id == uid,
                Event.status != EventStatus.cancelled,
                Event.start_time_utc < range_end_utc,
                Event.end_time_utc > range_start_utc,
            )
            .all()
        )

        for ev in events:
            result["busy_blocks"].append({
                "user_id": str(uid),
                "display_name": user.display_name,
                "event_id": str(ev.event_id),
                "title": ev.title,
                "start": ev.start_time_utc.isoformat(),
                "end": ev.end_time_utc.isoformat(),
                "constraint_level": ev.constraint_level.value,
            })

        # Check DND conflicts
        if user.dnd_window_start_local and user.dnd_window_end_local:
            tz = pytz.timezone(user.default_timezone)
            local_start = range_start_utc.astimezone(tz).time()
            local_end = range_end_utc.astimezone(tz).time()
            dnd_start = user.dnd_window_start_local
            dnd_end = user.dnd_window_end_local

            if _times_overlap(local_start, local_end, dnd_start, dnd_end):
                result["dnd_conflicts"].append({
                    "user_id": str(uid),
                    "display_name": user.display_name,
                    "dnd_window": f"{dnd_start.isoformat()}-{dnd_end.isoformat()}",
                    "timezone": user.default_timezone,
                })

    logger.info("Availability check for %d users in range %s to %s", len(user_ids), range_start_utc, range_end_utc)
    return result


def _times_overlap(start1, end1, start2, end2) -> bool:
    """Check if two time ranges overlap (handles overnight windows like 22:00-07:00)."""
    if start2 <= end2:
        return start1 < end2 and end1 > start2
    else:
        return start1 < end2 or end1 > start2
