"""CreateEvent tool — spec §6.3.

Creates a new event via the event_service (which enforces all invariants).
"""
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session
from app.services.event_service import create_event


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "CreateEvent",
        "description": (
            "Create a new calendar event. The event_service enforces constraint "
            "resolution, DND checks, and writes the mutation ledger automatically. "
            "Returns the created event object."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "group_id": {
                    "type": "string",
                    "description": "UUID of the group this event belongs to.",
                },
                "title": {
                    "type": "string",
                    "description": "Event title.",
                },
                "start_time_utc": {
                    "type": "string",
                    "description": "ISO-8601 UTC start time, e.g. 2026-03-01T19:00:00Z",
                },
                "end_time_utc": {
                    "type": "string",
                    "description": "ISO-8601 UTC end time, e.g. 2026-03-01T20:00:00Z",
                },
                "organizer_id": {
                    "type": "string",
                    "description": "UUID of the organizing user.",
                },
                "attendee_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee user UUIDs (defaults to just the organizer).",
                },
                "constraint_level": {
                    "type": "string",
                    "enum": ["Hard", "Soft"],
                    "description": "Hard = cannot overlap other Hard or DND. Soft = may overlap. Default: Soft.",
                },
                "event_type": {
                    "type": "string",
                    "enum": ["default", "outOfOffice", "focusTime"],
                    "description": "Type of event. Default: default.",
                },
            },
            "required": ["group_id", "title", "start_time_utc", "end_time_utc", "organizer_id"],
        },
    },
}


def execute(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    """Create the event and return a summary dict."""
    event = create_event(
        db=db,
        group_id=args["group_id"],
        title=args["title"],
        start_utc=datetime.fromisoformat(args["start_time_utc"].replace("Z", "+00:00")),
        end_utc=datetime.fromisoformat(args["end_time_utc"].replace("Z", "+00:00")),
        organizer_id=args["organizer_id"],
        attendee_ids=args.get("attendee_ids", []),
        constraint_level=args.get("constraint_level", "Soft"),
        event_type=args.get("event_type", "default"),
    )
    return {
        "event_id": str(event.event_id),
        "title": event.title,
        "start_time_utc": event.start_time_utc.isoformat(),
        "end_time_utc": event.end_time_utc.isoformat(),
        "status": event.status.value,
        "constraint_level": event.constraint_level.value,
        "version": event.version,
    }
