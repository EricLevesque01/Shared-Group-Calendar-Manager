"""SummarizeSchedule tool — spec §6.6.

Read-only schedule summary for a user or group over a date range.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session
from app.models.event import Event, EventStatus
from app.models.attendee import EventAttendee
from app.models.group import Group


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "SummarizeSchedule",
        "description": (
            "Get a read-only summary of upcoming events for a user or group. "
            "Useful for answering questions like 'What's on my schedule this week?'"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "UUID of the user whose schedule to summarize (optional if group_id given).",
                },
                "group_id": {
                    "type": "string",
                    "description": "UUID of the group whose schedule to summarize (optional if user_id given).",
                },
                "range_start_utc": {
                    "type": "string",
                    "description": "ISO-8601 UTC start, defaults to now.",
                },
                "range_end_utc": {
                    "type": "string",
                    "description": "ISO-8601 UTC end, defaults to 7 days from now.",
                },
            },
        },
    },
}


def execute(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    """Build a human-readable schedule summary."""
    now = datetime.now(timezone.utc)
    range_start = (
        datetime.fromisoformat(args["range_start_utc"].replace("Z", "+00:00"))
        if args.get("range_start_utc")
        else now
    )
    range_end = (
        datetime.fromisoformat(args["range_end_utc"].replace("Z", "+00:00"))
        if args.get("range_end_utc")
        else now + timedelta(days=7)
    )

    query = db.query(Event).filter(
        Event.status != EventStatus.cancelled,
        Event.start_time_utc < range_end,
        Event.end_time_utc > range_start,
    )

    if args.get("user_id"):
        uid = uuid.UUID(args["user_id"])
        query = query.join(EventAttendee).filter(EventAttendee.user_id == uid)
    elif args.get("group_id"):
        gid = uuid.UUID(args["group_id"])
        query = query.filter(Event.group_id == gid)

    events = query.order_by(Event.start_time_utc).all()

    summary_events = []
    for ev in events:
        summary_events.append({
            "event_id": str(ev.event_id),
            "title": ev.title,
            "start": ev.start_time_utc.isoformat(),
            "end": ev.end_time_utc.isoformat(),
            "status": ev.status.value,
            "constraint_level": ev.constraint_level.value,
        })

    return {
        "range": f"{range_start.isoformat()} to {range_end.isoformat()}",
        "total_events": len(summary_events),
        "events": summary_events,
    }
