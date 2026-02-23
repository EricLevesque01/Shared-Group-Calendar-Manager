"""UpdateEvent tool — spec §6.4.

Updates an existing event via event_service (optimistic locking + auth).
"""
import uuid
from typing import Any

from sqlalchemy.orm import Session
from app.services.event_service import update_event


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "UpdateEvent",
        "description": (
            "Update fields on an existing event. Requires the current version "
            "number (optimistic locking). Only the organizer may update the event."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "UUID of the event to update.",
                },
                "actor_user_id": {
                    "type": "string",
                    "description": "UUID of the user performing the update (must be organizer).",
                },
                "version": {
                    "type": "integer",
                    "description": "Current version for optimistic locking.",
                },
                "updates": {
                    "type": "object",
                    "description": "Key-value pairs of fields to update (title, start_time_utc, end_time_utc, etc).",
                },
            },
            "required": ["event_id", "actor_user_id", "version", "updates"],
        },
    },
}


def execute(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    """Update the event and return updated snapshot."""
    event = update_event(
        db=db,
        event_id=uuid.UUID(args["event_id"]),
        actor_user_id=uuid.UUID(args["actor_user_id"]),
        version=args["version"],
        updates=args["updates"],
    )
    return {
        "event_id": str(event.event_id),
        "title": event.title,
        "status": event.status.value,
        "version": event.version,
    }
