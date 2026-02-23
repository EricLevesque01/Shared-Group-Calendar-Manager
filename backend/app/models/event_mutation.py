"""EventMutation ORM model — spec §5.6 (Ledger of Truth)."""
import uuid
import enum
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from app.database import Base


class ActionType(str, enum.Enum):
    create = "create"
    update = "update"
    cancel = "cancel"


class EventMutation(Base):
    __tablename__ = "event_mutations"

    mutation_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(36), ForeignKey("events.event_id"), nullable=False)
    actor_user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    action_type = Column(SAEnum(ActionType), nullable=False)
    before_snapshot = Column(JSON, nullable=True)
    after_snapshot = Column(JSON, nullable=False)
    idempotency_key = Column(String(255), nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
