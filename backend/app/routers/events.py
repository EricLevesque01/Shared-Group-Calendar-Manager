"""Event API routes — delegates to event_service for invariant enforcement."""
import logging
from uuid import UUID
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import Event, EventStatus
from app.schemas.event import EventCreate, EventUpdate, EventOut, EventCancelRequest
from app.services import event_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    """Create a new event with attendees and all invariant checks."""
    event = event_service.create_event(
        db=db,
        group_id=payload.group_id,
        title=payload.title,
        start_utc=payload.start_time_utc,
        end_utc=payload.end_time_utc,
        organizer_id=payload.organizer_id,
        attendee_ids=payload.attendee_ids,
        constraint_level=payload.constraint_level,
        event_type=payload.event_type,
        event_status=payload.status,
        location_type=payload.location_type,
        location_text=payload.location_text,
    )
    return event


@router.get("/", response_model=list[EventOut])
def list_events(
    group_id: Optional[UUID] = Query(None),
    start_after: Optional[datetime] = Query(None),
    start_before: Optional[datetime] = Query(None),
    include_cancelled: bool = Query(False),
    db: Session = Depends(get_db),
):
    """List events with optional filters."""
    query = db.query(Event)
    if group_id:
        query = query.filter(Event.group_id == group_id)
    if start_after:
        query = query.filter(Event.start_time_utc >= start_after)
    if start_before:
        query = query.filter(Event.start_time_utc <= start_before)
    if not include_cancelled:
        query = query.filter(Event.status != EventStatus.cancelled)
    return query.order_by(Event.start_time_utc).all()


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: UUID, db: Session = Depends(get_db)):
    """Fetch a single event by ID with attendees."""
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/{event_id}", response_model=EventOut)
def update_event(
    event_id: UUID,
    payload: EventUpdate,
    actor_user_id: UUID = Query(..., description="ID of the user performing the update"),
    db: Session = Depends(get_db),
):
    """Update an event (organizer only, optimistic locking enforced)."""
    updates = payload.model_dump(exclude_unset=True, exclude={"version"})
    return event_service.update_event(
        db=db,
        event_id=event_id,
        actor_user_id=actor_user_id,
        version=payload.version,
        updates=updates,
    )


@router.post("/{event_id}/cancel", response_model=EventOut)
def cancel_event(event_id: UUID, payload: EventCancelRequest, db: Session = Depends(get_db)):
    """Cancel an event (soft delete, organizer only, optimistic locking enforced)."""
    return event_service.cancel_event(
        db=db,
        event_id=event_id,
        actor_user_id=payload.cancelled_by_user_id,
        version=payload.version,
        cancel_reason=payload.cancel_reason,
    )
