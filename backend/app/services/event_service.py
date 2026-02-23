"""Core event service — enforces all spec invariants.

Responsibilities (per spec §6, §7, §15):
- Authorization hook: only organizer may update/cancel/confirm
- Constraint resolution: Hard vs Soft overlap rules
- DND window evaluation (backend-side timezone conversion)
- Optimistic locking via version field
- Mutation ledger (EventMutations) for every write
- Cancellation safety (soft delete + metadata)
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

import pytz
from sqlalchemy import and_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.event import Event, EventStatus, ConstraintLevel
from app.models.attendee import EventAttendee, RSVPStatus
from app.models.event_mutation import EventMutation, ActionType
from app.models.user import User

logger = logging.getLogger(__name__)


def _event_snapshot(event: Event) -> dict[str, Any]:
    """Serialize an event to a JSON-safe dict for the mutation ledger."""
    return {
        "event_id": str(event.event_id),
        "title": event.title,
        "start_time_utc": event.start_time_utc.isoformat() if event.start_time_utc else None,
        "end_time_utc": event.end_time_utc.isoformat() if event.end_time_utc else None,
        "status": event.status.value if event.status else None,
        "constraint_level": event.constraint_level.value if event.constraint_level else None,
        "version": event.version,
    }


def _check_authorization(event: Event, actor_user_id: uuid.UUID) -> None:
    """§7.1 — Only organizer may update/cancel/confirm."""
    if event.organizer_id != actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organizer may modify this event. Create a ChangeRequest instead.",
        )


def _check_dnd_conflict(
    db: Session,
    user_ids: list[uuid.UUID],
    start_utc: datetime,
    end_utc: datetime,
) -> list[dict]:
    """§7.4 — Evaluate DND window conflicts for attendees.

    Process: convert UTC event time → user's local time, compare to DND window.
    Agent never performs timezone math — this is the backend's responsibility.
    """
    conflicts = []
    for uid in user_ids:
        user = db.query(User).filter(User.user_id == uid).first()
        if not user or not user.dnd_window_start_local or not user.dnd_window_end_local:
            continue

        tz = pytz.timezone(user.default_timezone)
        local_start = start_utc.astimezone(tz).time()
        local_end = end_utc.astimezone(tz).time()
        dnd_start = user.dnd_window_start_local
        dnd_end = user.dnd_window_end_local

        # Check if event overlaps with DND window
        if _times_overlap(local_start, local_end, dnd_start, dnd_end):
            conflicts.append({
                "user_id": str(uid),
                "display_name": user.display_name,
                "dnd_window": f"{dnd_start.isoformat()}-{dnd_end.isoformat()}",
                "timezone": user.default_timezone,
            })

    return conflicts


def _times_overlap(start1, end1, start2, end2) -> bool:
    """Check if two time ranges overlap (handles overnight DND windows)."""
    if start2 <= end2:
        # Normal window (e.g. 22:00 - 23:00)
        return start1 < end2 and end1 > start2
    else:
        # Overnight window (e.g. 22:00 - 07:00)
        return start1 < end2 or end1 > start2


def _check_hard_constraints(
    db: Session,
    user_ids: list[uuid.UUID],
    start_utc: datetime,
    end_utc: datetime,
    exclude_event_id: Optional[uuid.UUID] = None,
) -> list[dict]:
    """§7.3 — Hard events cannot overlap other Hard events or DND windows."""
    conflicts = []
    for uid in user_ids:
        query = db.query(Event).join(EventAttendee).filter(
            EventAttendee.user_id == uid,
            Event.status != EventStatus.cancelled,
            Event.constraint_level == ConstraintLevel.hard,
            Event.start_time_utc < end_utc,
            Event.end_time_utc > start_utc,
        )
        if exclude_event_id:
            query = query.filter(Event.event_id != exclude_event_id)

        overlapping = query.all()
        for ev in overlapping:
            conflicts.append({
                "user_id": str(uid),
                "conflicting_event_id": str(ev.event_id),
                "conflicting_title": ev.title,
                "start": ev.start_time_utc.isoformat(),
                "end": ev.end_time_utc.isoformat(),
            })
    return conflicts


def create_event(
    db: Session,
    group_id: uuid.UUID,
    title: str,
    start_utc: datetime,
    end_utc: datetime,
    organizer_id: uuid.UUID,
    attendee_ids: list[uuid.UUID],
    constraint_level: str = "Soft",
    event_type: str = "default",
    event_status: str = "Proposed",
    location_type: Optional[str] = None,
    location_text: Optional[str] = None,
) -> Event:
    """Create an event with full invariant checks and mutation logging."""
    all_user_ids = list(set([organizer_id] + attendee_ids))

    # §7.4 — DND check
    dnd_conflicts = _check_dnd_conflict(db, all_user_ids, start_utc, end_utc)
    if dnd_conflicts and constraint_level == "Hard":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Hard event conflicts with DND windows", "conflicts": dnd_conflicts},
        )

    # §7.3 — Hard constraint overlap check
    if constraint_level == "Hard":
        hard_conflicts = _check_hard_constraints(db, all_user_ids, start_utc, end_utc)
        if hard_conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Hard event conflicts with existing Hard events", "conflicts": hard_conflicts},
            )

    # Create event — §6.3
    event = Event(
        group_id=group_id,
        title=title,
        start_time_utc=start_utc,
        end_time_utc=end_utc,
        organizer_id=organizer_id,
        status=EventStatus(event_status),
        constraint_level=ConstraintLevel(constraint_level),
        event_type=event_type,
        location_type=location_type,
        location_text=location_text,
        version=1,
    )
    db.add(event)
    db.flush()

    # Create attendees — §6.3
    for uid in all_user_ids:
        attendee = EventAttendee(
            event_id=event.event_id,
            user_id=uid,
            rsvp_status=RSVPStatus.going if uid == organizer_id else RSVPStatus.invited,
            is_required=True,
        )
        db.add(attendee)

    # Write mutation — §6.3
    mutation = EventMutation(
        event_id=event.event_id,
        actor_user_id=organizer_id,
        action_type=ActionType.create,
        before_snapshot=None,
        after_snapshot=_event_snapshot(event),
        idempotency_key=str(uuid.uuid4()),
    )
    db.add(mutation)
    db.commit()
    db.refresh(event)
    logger.info("Created event '%s' (%s) by organizer %s", title, event.event_id, organizer_id)
    return event


def update_event(
    db: Session,
    event_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    version: int,
    updates: dict[str, Any],
) -> Event:
    """Update an event with optimistic locking, authorization, and mutation logging."""
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # §7.1 — Authorization
    _check_authorization(event, actor_user_id)

    # §15 — Optimistic locking
    if event.version != version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version mismatch: expected {event.version}, got {version}. Re-fetch and retry.",
        )

    before = _event_snapshot(event)

    # Apply updates
    for field, value in updates.items():
        if hasattr(event, field) and field not in ("event_id", "version", "created_at"):
            setattr(event, field, value)

    # §6.4 — Increment version
    event.version += 1
    event.updated_at = datetime.now(timezone.utc)

    # §6.4 — Write mutation
    mutation = EventMutation(
        event_id=event.event_id,
        actor_user_id=actor_user_id,
        action_type=ActionType.update,
        before_snapshot=before,
        after_snapshot=_event_snapshot(event),
        idempotency_key=str(uuid.uuid4()),
    )
    db.add(mutation)
    db.commit()
    db.refresh(event)
    logger.info("Updated event %s to version %d", event_id, event.version)
    return event


def cancel_event(
    db: Session,
    event_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    version: int,
    cancel_reason: Optional[str] = None,
) -> Event:
    """Soft-delete an event with authorization, optimistic locking, and mutation logging."""
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # §7.1 — Authorization
    _check_authorization(event, actor_user_id)

    # §7.2 — Cancellation safety: event must not already be cancelled
    if event.status == EventStatus.cancelled:
        raise HTTPException(status_code=400, detail="Event is already cancelled")

    # §15 — Optimistic locking
    if event.version != version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version mismatch: expected {event.version}, got {version}. Re-fetch and retry.",
        )

    before = _event_snapshot(event)

    # §6.5 — Soft delete
    event.status = EventStatus.cancelled
    event.cancelled_at = datetime.now(timezone.utc)
    event.cancelled_by_user_id = actor_user_id
    event.cancel_reason = cancel_reason
    event.version += 1
    event.updated_at = datetime.now(timezone.utc)

    # §6.5 — Write mutation
    mutation = EventMutation(
        event_id=event.event_id,
        actor_user_id=actor_user_id,
        action_type=ActionType.cancel,
        before_snapshot=before,
        after_snapshot=_event_snapshot(event),
        idempotency_key=str(uuid.uuid4()),
    )
    db.add(mutation)
    db.commit()
    db.refresh(event)
    logger.info("Cancelled event %s (reason: %s)", event_id, cancel_reason)
    return event
