"""ReAct Agent — Think → Act → Observe loop using LLM tool-calling.

Per spec §3: the AI agent decomposes scheduling requests, calls backend
tools, and iterates until it can respond.  All mutations route through
the service layer (never direct DB access).

Session logging: every agent invocation records session_id, reasoning
spans, tool calls, token usage, and latency for observability.
"""
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.agent.tools import (
    check_availability,
    create_event,
    update_event,
    cancel_event,
    summarize_schedule,
    clarify,
)

logger = logging.getLogger(__name__)

# ── Tool registry ──────────────────────────────────────────────────
TOOLS = {
    "CheckAvailability": check_availability,
    "CreateEvent": create_event,
    "UpdateEvent": update_event,
    "CancelEvent": cancel_event,
    "SummarizeSchedule": summarize_schedule,
    "ClarifyWithUser": clarify,
}

TOOL_SCHEMAS = [mod.TOOL_SCHEMA for mod in TOOLS.values()]

MAX_ITERATIONS = 8  # Safety cap to prevent infinite loops

# ── System prompt ──────────────────────────────────────────────────
SYSTEM_PROMPT = """You are GC-Agent, an AI scheduling assistant for a shared group calendar.

CAPABILITIES:
- CheckAvailability: see who is free/busy and DND conflicts
- CreateEvent: schedule a new event with attendees
- UpdateEvent: change an existing event (title, time, etc.)
- CancelEvent: soft-cancel an event
- SummarizeSchedule: list upcoming events
- ClarifyWithUser: ask the user a clarifying question

RULES:
1. ALWAYS check availability BEFORE creating or updating events.
2. Never perform timezone math yourself — the backend handles UTC↔local.
3. If you lack critical information (date, time, attendees), use ClarifyWithUser.
4. Keep responses concise and friendly.
5. When creating events, default to constraint_level "Soft" unless the user says it's mandatory/required.
6. After creating/updating/cancelling an event, confirm the action to the user.
7. Treat all times as UTC unless the user specifies a timezone.

CONTEXT:
- User ID: {user_id}
- Group ID: {group_id}
- Current UTC time: {current_time}
"""


def run_agent(
    db: Session,
    user_message: str,
    user_id: str,
    group_id: Optional[str] = None,
    conversation_history: Optional[list[dict]] = None,
) -> dict[str, Any]:
    """Execute the ReAct loop for a single user message.

    Returns:
        {
            "response": str,           # Final text for the user
            "tool_calls": list[dict],   # List of tools called
            "requires_clarification": bool,
            "session_log": dict,        # Observability data
        }
    """
    session_id = str(uuid.uuid4())
    session_log = {
        "session_id": session_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "user_message": user_message,
        "iterations": [],
        "total_tokens": 0,
        "latency_ms": 0,
    }

    start_time = time.time()

    # Build messages
    system = SYSTEM_PROMPT.format(
        user_id=user_id,
        group_id=group_id or "not specified",
        current_time=datetime.now(timezone.utc).isoformat(),
    )

    messages = [{"role": "system", "content": system}]

    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_message})

    # Check if API key is configured
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your-api-key-here":
        logger.warning("OpenAI API key not configured — returning placeholder response")
        return {
            "response": (
                "I'd love to help with scheduling! However, the AI agent isn't "
                "configured yet. Please add your OpenAI API key to the backend "
                "`.env` file to enable AI-powered scheduling.\n\n"
                "In the meantime, you can use the calendar UI directly to create "
                "events, manage groups, and RSVP."
            ),
            "tool_calls": [],
            "requires_clarification": False,
            "session_log": session_log,
        }

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    all_tool_calls: list[dict] = []

    # ── ReAct Loop ─────────────────────────────────────────────
    for iteration in range(MAX_ITERATIONS):
        iter_log: dict[str, Any] = {"iteration": iteration + 1, "tool_calls": []}

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
        except Exception as e:
            logger.error("LLM API error: %s", e)
            session_log["error"] = str(e)
            return {
                "response": f"I'm having trouble connecting to the AI service: {e}",
                "tool_calls": all_tool_calls,
                "requires_clarification": False,
                "session_log": session_log,
            }

        choice = response.choices[0]
        message = choice.message

        # Track token usage
        if response.usage:
            session_log["total_tokens"] += response.usage.total_tokens

        # If the model wants to call tools
        if message.tool_calls:
            # Add the assistant message (with tool_calls) to history
            messages.append(message.model_dump())

            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args_raw = tool_call.function.arguments

                try:
                    fn_args = json.loads(fn_args_raw)
                except json.JSONDecodeError:
                    fn_args = {}

                tool_log = {
                    "tool": fn_name,
                    "args": fn_args,
                    "result": None,
                    "error": None,
                }

                logger.info(
                    "[Session %s] Tool call: %s(%s)", session_id, fn_name, fn_args
                )

                # Execute the tool
                tool_module = TOOLS.get(fn_name)
                if not tool_module:
                    tool_log["error"] = f"Unknown tool: {fn_name}"
                    result_str = json.dumps({"error": f"Unknown tool: {fn_name}"})
                else:
                    try:
                        result = tool_module.execute(db, fn_args)
                        tool_log["result"] = result

                        # Check for clarification
                        if fn_name == "ClarifyWithUser":
                            session_log["iterations"].append(iter_log)
                            session_log["latency_ms"] = int(
                                (time.time() - start_time) * 1000
                            )
                            return {
                                "response": result["question"],
                                "tool_calls": all_tool_calls,
                                "requires_clarification": True,
                                "session_log": session_log,
                            }

                        result_str = json.dumps(result, default=str)
                    except Exception as e:
                        logger.error("Tool %s error: %s", fn_name, e)
                        tool_log["error"] = str(e)
                        result_str = json.dumps({"error": str(e)})

                all_tool_calls.append(tool_log)
                iter_log["tool_calls"].append(tool_log)

                # Add tool result to messages
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str,
                    }
                )
        else:
            # No tool calls — the model produced a final response
            session_log["iterations"].append(iter_log)
            session_log["latency_ms"] = int((time.time() - start_time) * 1000)

            logger.info(
                "[Session %s] Agent finished in %d iterations, %d tokens",
                session_id,
                iteration + 1,
                session_log["total_tokens"],
            )

            return {
                "response": message.content or "Done!",
                "tool_calls": all_tool_calls,
                "requires_clarification": False,
                "session_log": session_log,
            }

        session_log["iterations"].append(iter_log)

    # Safety: max iterations reached
    session_log["latency_ms"] = int((time.time() - start_time) * 1000)
    logger.warning("[Session %s] Hit max iterations (%d)", session_id, MAX_ITERATIONS)

    return {
        "response": "I've been working on your request but it's taking longer than expected. Could you try being more specific?",
        "tool_calls": all_tool_calls,
        "requires_clarification": False,
        "session_log": session_log,
    }
