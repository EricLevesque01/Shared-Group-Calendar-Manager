"""ChangeRequest API routes — HITL workflow per spec §10."""
import logging
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.change_request import ChangeRequest, RequestStatus, RequestType
from app.models.event import Event
from app.services import event_service
from app.schemas.change_request import ChangeRequestCreate, ChangeRequestOut

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ChangeRequestOut, status_code=status.HTTP_201_CREATED)
def create_change_request(payload: ChangeRequestCreate, db: Session = Depends(get_db)):
    """Create a change request when a non-organizer wants to modify an event.

    Per spec §10: unauthorized user requests mutation → create ChangeRequest → notify organizer.
    """
    event = db.query(Event).filter(Event.event_id == payload.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    cr = ChangeRequest(
        event_id=payload.event_id,
        requester_id=payload.requester_id,
        request_type=RequestType(payload.request_type),
        payload=payload.payload,
        status=RequestStatus.pending,
    )
    db.add(cr)
    db.commit()
    db.refresh(cr)
    logger.info("ChangeRequest %s created for event %s by user %s", cr.request_id, payload.event_id, payload.requester_id)
    return cr


@router.get("/", response_model=list[ChangeRequestOut])
def list_change_requests(
    event_id: UUID | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    """List change requests, optionally filtered by event or status."""
    query = db.query(ChangeRequest)
    if event_id:
        query = query.filter(ChangeRequest.event_id == event_id)
    if status_filter:
        query = query.filter(ChangeRequest.status == RequestStatus(status_filter))
    return query.order_by(ChangeRequest.created_at.desc()).all()


@router.post("/{request_id}/approve", response_model=ChangeRequestOut)
def approve_change_request(request_id: UUID, db: Session = Depends(get_db)):
    """Approve a pending change request — applies the mutation via event_service.

    Per spec §10: organizer approves → apply mutation → write EventMutation entry.
    Backend generates approval based on raw payload (prevents lies-in-the-loop).
    """
    cr = db.query(ChangeRequest).filter(ChangeRequest.request_id == request_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="ChangeRequest not found")
    if cr.status != RequestStatus.pending:
        raise HTTPException(status_code=400, detail=f"ChangeRequest is already {cr.status.value}")

    event = db.query(Event).filter(Event.event_id == cr.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Associated event not found")

    # Apply the mutation based on request type
    if cr.request_type == RequestType.cancel:
        event_service.cancel_event(
            db=db,
            event_id=cr.event_id,
            actor_user_id=event.organizer_id,  # Applied as organizer action
            version=event.version,
            cancel_reason=cr.payload.get("reason", "Approved change request"),
        )
    elif cr.request_type in (RequestType.time_change, RequestType.update_details):
        event_service.update_event(
            db=db,
            event_id=cr.event_id,
            actor_user_id=event.organizer_id,
            version=event.version,
            updates=cr.payload,
        )

    cr.status = RequestStatus.approved
    db.commit()
    db.refresh(cr)
    logger.info("ChangeRequest %s approved", request_id)
    return cr


@router.post("/{request_id}/reject", response_model=ChangeRequestOut)
def reject_change_request(request_id: UUID, db: Session = Depends(get_db)):
    """Reject a pending change request."""
    cr = db.query(ChangeRequest).filter(ChangeRequest.request_id == request_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="ChangeRequest not found")
    if cr.status != RequestStatus.pending:
        raise HTTPException(status_code=400, detail=f"ChangeRequest is already {cr.status.value}")

    cr.status = RequestStatus.rejected
    db.commit()
    db.refresh(cr)
    logger.info("ChangeRequest %s rejected", request_id)
    return cr
