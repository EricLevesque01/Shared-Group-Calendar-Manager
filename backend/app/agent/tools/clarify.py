"""ClarifyWithUser tool — spec §6.2.

Suspends the agent loop and returns a question to the user.
This is a special tool — when invoked, the agent should stop iterating
and return the clarification question to the frontend.
"""
from typing import Any
from sqlalchemy.orm import Session


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "ClarifyWithUser",
        "description": (
            "Ask the user a clarifying question before proceeding. Use this "
            "when you need more information to complete a task, such as the exact "
            "time, date, attendees, or constraint preferences."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to ask the user.",
                },
            },
            "required": ["question"],
        },
    },
}


def execute(db: Session, args: dict[str, Any]) -> dict[str, Any]:
    """Return the clarification payload — the agent loop handles suspension."""
    return {
        "requires_clarification": True,
        "question": args["question"],
    }
