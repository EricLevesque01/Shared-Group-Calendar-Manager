"""CancelEvent tool — spec §6.5.

Soft-cancels an event via event_service (auth + optimistic lock).
"""
import uuid
from typing import Any

from sqlalchemy.orm import Session
from app.services.event_service import cancel_event


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "CancelEvent",
        "description": (
            "Cancel (soft-delete) an existing event. Sets status to Cancelled, "
            "records metadata. Requires organizer authorization and version for "
            "optimistic locking."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "UUID of the event to cancel.",
                },
                "actor_user_id": {
                    "type": "string",
                    "description": "UUID of the user cancelling (must be organizer).",
                },
                "version": {
                    "type": "integer",
                    "description": "Current version for optimistic locking.",
                },
                "cancel_reason": {
                    "type": "string",
                    "description": "Reason for cancellation.",
                },
            },
            "required": ["event_id", "actor_user_id", "version"],
        },
    },
}


def execute(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    """Cancel the event and return confirmation."""
    event = cancel_event(
        db=db,
        event_id=uuid.UUID(args["event_id"]),
        actor_user_id=uuid.UUID(args["actor_user_id"]),
        version=args["version"],
        cancel_reason=args.get("cancel_reason"),
    )
    return {
        "event_id": str(event.event_id),
        "title": event.title,
        "status": event.status.value,
        "cancelled_at": event.cancelled_at.isoformat() if event.cancelled_at else None,
    }
