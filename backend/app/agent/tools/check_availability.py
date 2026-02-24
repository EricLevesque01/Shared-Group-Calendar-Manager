"""CheckAvailability tool — spec §6.1.

Returns busy blocks, DND conflicts, and constraint flags for users
in a given time range.  Agent uses this to avoid proposing conflicting slots.
"""
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session
from app.services.availability_service import check_availability


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "CheckAvailability",
        "description": (
            "Check the availability of one or more users in a time range. "
            "Returns busy blocks (existing events), DND window conflicts, "
            "and constraint flags. Call this BEFORE creating or updating events when needed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of user UUIDs to check.",
                },
                "range_start_utc": {
                    "type": "string",
                    "description": "ISO-8601 UTC start of the window, e.g. 2026-03-01T09:00:00Z",
                },
                "range_end_utc": {
                    "type": "string",
                    "description": "ISO-8601 UTC end of the window, e.g. 2026-03-01T17:00:00Z",
                },
            },
            "required": ["user_ids", "range_start_utc", "range_end_utc"],
        },
    },
}


def execute(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    """Run the availability check and return structured results."""
    user_ids = args["user_ids"]  # plain strings — no UUID wrapping needed
    range_start = datetime.fromisoformat(args["range_start_utc"].replace("Z", "+00:00"))
    range_end = datetime.fromisoformat(args["range_end_utc"].replace("Z", "+00:00"))

    return check_availability(db, user_ids, range_start, range_end)
