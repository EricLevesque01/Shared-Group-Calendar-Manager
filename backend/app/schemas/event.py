"""Pydantic schemas for Events."""
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class EventCreate(BaseModel):
    group_id: UUID
    title: str
    start_time_utc: datetime
    end_time_utc: datetime
    organizer_id: UUID
    status: str = "Proposed"
    constraint_level: str = "Soft"
    event_type: str = "default"
    location_type: Optional[str] = None
    location_text: Optional[str] = None
    attendee_ids: list[UUID] = []


class EventUpdate(BaseModel):
    title: Optional[str] = None
    start_time_utc: Optional[datetime] = None
    end_time_utc: Optional[datetime] = None
    status: Optional[str] = None
    constraint_level: Optional[str] = None
    event_type: Optional[str] = None
    location_type: Optional[str] = None
    location_text: Optional[str] = None
    version: int  # required for optimistic locking


class EventOut(BaseModel):
    event_id: UUID
    group_id: UUID
    title: str
    start_time_utc: datetime
    end_time_utc: datetime
    organizer_id: UUID
    status: str
    constraint_level: str
    event_type: str
    location_type: Optional[str] = None
    location_text: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by_user_id: Optional[UUID] = None
    cancel_reason: Optional[str] = None
    version: int
    created_at: datetime
    updated_at: datetime
    attendees: list[AttendeeOut] = []

    model_config = {"from_attributes": True}


class AttendeeOut(BaseModel):
    user_id: UUID
    rsvp_status: str
    is_required: bool
    responded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EventCancelRequest(BaseModel):
    cancelled_by_user_id: UUID
    cancel_reason: Optional[str] = None
    version: int  # required for optimistic locking


# Rebuild EventOut now that AttendeeOut is defined
EventOut.model_rebuild()
