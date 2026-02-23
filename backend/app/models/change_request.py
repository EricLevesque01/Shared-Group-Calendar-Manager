"""ChangeRequest ORM model — spec §5.5."""
import uuid
import enum
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from app.database import Base


class RequestType(str, enum.Enum):
    time_change = "time_change"
    cancel = "cancel"
    update_details = "update_details"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    request_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(36), ForeignKey("events.event_id"), nullable=False)
    requester_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    request_type = Column(SAEnum(RequestType), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(SAEnum(RequestStatus), nullable=False, default=RequestStatus.pending)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
