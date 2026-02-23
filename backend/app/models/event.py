"""Event ORM model — spec §5.3."""
import uuid
import enum
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class EventStatus(str, enum.Enum):
    proposed = "Proposed"
    confirmed = "Confirmed"
    cancelled = "Cancelled"


class ConstraintLevel(str, enum.Enum):
    hard = "Hard"
    soft = "Soft"


class EventType(str, enum.Enum):
    default = "default"
    out_of_office = "outOfOffice"
    focus_time = "focusTime"


class LocationType(str, enum.Enum):
    remote = "remote"
    in_person = "in_person"


class Event(Base):
    __tablename__ = "events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.group_id"), nullable=False)
    title = Column(String(255), nullable=False)
    start_time_utc = Column(DateTime(timezone=True), nullable=False)
    end_time_utc = Column(DateTime(timezone=True), nullable=False)
    organizer_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    status = Column(SAEnum(EventStatus), nullable=False, default=EventStatus.proposed)
    constraint_level = Column(SAEnum(ConstraintLevel), nullable=False, default=ConstraintLevel.soft)
    event_type = Column(SAEnum(EventType), nullable=False, default=EventType.default)
    location_type = Column(SAEnum(LocationType), nullable=True)
    location_text = Column(String(500), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    cancel_reason = Column(String(500), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    attendees = relationship("EventAttendee", back_populates="event", cascade="all, delete-orphan")
