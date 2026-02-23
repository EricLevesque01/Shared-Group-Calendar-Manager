"""User ORM model — spec §5.1."""
import uuid
from sqlalchemy import Column, String, Time, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String(100), nullable=False)
    default_timezone = Column(String(50), nullable=False, default="UTC")  # IANA tz
    dnd_window_start_local = Column(Time, nullable=True)
    dnd_window_end_local = Column(Time, nullable=True)
    aliases = Column(JSON, nullable=True, default=list)
    enable_transit_checks = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
