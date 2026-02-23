"""AI Agent API routes — wires the ReAct agent to the HTTP layer."""
import logging
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.agent.react_agent import run_agent

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    user_id: str
    group_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[dict] = []
    requires_clarification: bool = False


@router.post("/chat", response_model=ChatResponse)
def agent_chat(payload: ChatMessage, db: Session = Depends(get_db)):
    """Send a message to the AI agent — runs the full ReAct loop."""
    logger.info("Agent chat from user %s: %s", payload.user_id, payload.message)

    result = run_agent(
        db=db,
        user_message=payload.message,
        user_id=payload.user_id,
        group_id=payload.group_id,
    )

    # Log session for observability
    session_log = result.get("session_log", {})
    logger.info(
        "Agent session %s completed: %d tool calls, %d tokens, %dms",
        session_log.get("session_id", "?"),
        len(result.get("tool_calls", [])),
        session_log.get("total_tokens", 0),
        session_log.get("latency_ms", 0),
    )

    return ChatResponse(
        response=result["response"],
        tool_calls=result.get("tool_calls", []),
        requires_clarification=result.get("requires_clarification", False),
    )
