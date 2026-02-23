"""AI Agent API route — placeholder for Phase 3 implementation."""
import logging
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    user_id: str
    group_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[dict] = []
    requires_clarification: bool = False


@router.post("/chat", response_model=ChatResponse)
def agent_chat(payload: ChatMessage):
    """Send a message to the AI agent (Phase 3 — to be implemented)."""
    logger.info("Agent chat from user %s: %s", payload.user_id, payload.message)
    return ChatResponse(
        response="AI Agent is not yet configured. Please add your API key to the .env file and Phase 3 will be implemented.",
        tool_calls=[],
        requires_clarification=False,
    )
