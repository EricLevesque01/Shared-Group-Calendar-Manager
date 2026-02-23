"""EventAttendee ORM model — spec §5.4."""
import enum
from sqlalchemy import Column, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class RSVPStatus(str, enum.Enum):
    invited = "invited"
    going = "going"
    maybe = "maybe"
    declined = "declined"


class EventAttendee(Base):
    __tablename__ = "event_attendees"

    event_id = Column(UUID(as_uuid=True), ForeignKey("events.event_id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), primary_key=True)
    rsvp_status = Column(SAEnum(RSVPStatus), nullable=False, default=RSVPStatus.invited)
    is_required = Column(Boolean, nullable=False, default=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)

    event = relationship("Event", back_populates="attendees")
