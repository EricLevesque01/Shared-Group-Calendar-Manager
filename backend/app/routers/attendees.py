"""Attendee / RSVP API routes."""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.attendee import EventAttendee, RSVPStatus
from app.models.event import Event

logger = logging.getLogger(__name__)
router = APIRouter()


class RSVPPayload(BaseModel):
    event_id: str
    user_id: str
    rsvp_status: str  # going, maybe, declined


@router.post("/rsvp", status_code=status.HTTP_200_OK)
def set_rsvp(payload: RSVPPayload, db: Session = Depends(get_db)):
    """Set or update a user's RSVP status for an event."""
    event = db.query(Event).filter(Event.event_id == payload.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    attendee = (
        db.query(EventAttendee)
        .filter(
            EventAttendee.event_id == payload.event_id,
            EventAttendee.user_id == payload.user_id,
        )
        .first()
    )

    if not attendee:
        raise HTTPException(status_code=404, detail="User is not an attendee of this event")

    try:
        attendee.rsvp_status = RSVPStatus(payload.rsvp_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid RSVP status: {payload.rsvp_status}")

    attendee.responded_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("User %s RSVP'd '%s' to event %s", payload.user_id, payload.rsvp_status, payload.event_id)
    return {"status": "ok", "rsvp_status": payload.rsvp_status}
