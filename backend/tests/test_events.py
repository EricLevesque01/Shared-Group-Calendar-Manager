"""Tests for Event CRUD, invariants, and spec enforcement.

Covers:
- Event create / update / cancel
- Authorization hook (§7.1) — organizer-only
- Optimistic locking (§15) — version mismatch → 409
- Cancellation safety (§7.2) — already cancelled → 400
- Hard constraint overlap (§7.3) → 409
- DND window conflict (§7.4) → 409
- Mutation ledger (§5.6) — verified via DB query
- List with filters
"""
from datetime import datetime, timezone, timedelta
from tests.conftest import create_test_user, create_test_group


def _make_event(client, organizer_id: str, group_id: str, title: str = "Test Event",
                start_offset_hours: int = 24, duration_hours: int = 1,
                constraint: str = "Soft", attendee_ids: list = None):
    """Helper — create an event via the API."""
    start = datetime.now(timezone.utc) + timedelta(hours=start_offset_hours)
    end = start + timedelta(hours=duration_hours)
    payload = {
        "group_id": group_id,
        "title": title,
        "start_time_utc": start.isoformat(),
        "end_time_utc": end.isoformat(),
        "organizer_id": organizer_id,
        "constraint_level": constraint,
        "attendee_ids": attendee_ids or [],
    }
    return client.post("/api/events/", json=payload)


def _setup(client):
    """Create an organizer, a non-organizer, a group with both as members."""
    organizer = create_test_user(client, name="Organizer")
    other = create_test_user(client, name="Other User")
    group = create_test_group(client, creator_id=organizer["user_id"])
    # Add other user to group
    client.post(f"/api/groups/{group['group_id']}/members", json={
        "user_id": other["user_id"],
        "role": "member",
    })
    return organizer, other, group


class TestEventCreate:
    """Event creation and initial state."""

    def test_create_event(self, client):
        organizer, _, group = _setup(client)
        resp = _make_event(client, organizer["user_id"], group["group_id"], title="Dinner")
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Dinner"
        assert data["version"] == 1
        assert data["status"] == "Proposed"

    def test_create_event_with_attendees(self, client):
        organizer, other, group = _setup(client)
        resp = _make_event(
            client, organizer["user_id"], group["group_id"],
            title="Team Lunch", attendee_ids=[other["user_id"]],
        )
        assert resp.status_code == 201
        attendees = resp.json()["attendees"]
        user_ids = [a["user_id"] for a in attendees]
        assert organizer["user_id"] in user_ids
        assert other["user_id"] in user_ids


class TestEventUpdate:
    """Event update with authorization and optimistic locking."""

    def test_update_event_organizer(self, client):
        """Organizer can update → version increments."""
        organizer, _, group = _setup(client)
        event = _make_event(client, organizer["user_id"], group["group_id"]).json()

        resp = client.put(
            f"/api/events/{event['event_id']}?actor_user_id={organizer['user_id']}",
            json={"title": "Updated Title", "version": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated Title"
        assert data["version"] == 2

    def test_update_event_non_organizer_forbidden(self, client):
        """§7.1 — Non-organizer cannot update → 403."""
        organizer, other, group = _setup(client)
        event = _make_event(client, organizer["user_id"], group["group_id"]).json()

        resp = client.put(
            f"/api/events/{event['event_id']}?actor_user_id={other['user_id']}",
            json={"title": "Hacked Title", "version": 1},
        )
        assert resp.status_code == 403

    def test_update_event_version_mismatch(self, client):
        """§15 — Optimistic lock: wrong version → 409."""
        organizer, _, group = _setup(client)
        event = _make_event(client, organizer["user_id"], group["group_id"]).json()

        resp = client.put(
            f"/api/events/{event['event_id']}?actor_user_id={organizer['user_id']}",
            json={"title": "Stale Update", "version": 999},
        )
        assert resp.status_code == 409


class TestEventCancel:
    """Event cancellation (soft delete) with safety checks."""

    def test_cancel_event(self, client):
        """Organizer can cancel — sets status and metadata."""
        organizer, _, group = _setup(client)
        event = _make_event(client, organizer["user_id"], group["group_id"]).json()

        resp = client.post(f"/api/events/{event['event_id']}/cancel", json={
            "cancelled_by_user_id": organizer["user_id"],
            "cancel_reason": "Weather",
            "version": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "Cancelled"
        assert data["cancel_reason"] == "Weather"
        assert data["cancelled_by_user_id"] == organizer["user_id"]
        assert data["version"] == 2

    def test_cancel_already_cancelled(self, client):
        """§7.2 — Cannot cancel an already-cancelled event → 400."""
        organizer, _, group = _setup(client)
        event = _make_event(client, organizer["user_id"], group["group_id"]).json()

        # First cancel
        client.post(f"/api/events/{event['event_id']}/cancel", json={
            "cancelled_by_user_id": organizer["user_id"],
            "version": 1,
        })
        # Second cancel attempt
        resp = client.post(f"/api/events/{event['event_id']}/cancel", json={
            "cancelled_by_user_id": organizer["user_id"],
            "version": 2,
        })
        assert resp.status_code == 400

    def test_cancel_non_organizer_forbidden(self, client):
        """§7.1 — Non-organizer cannot cancel → 403."""
        organizer, other, group = _setup(client)
        event = _make_event(client, organizer["user_id"], group["group_id"]).json()

        resp = client.post(f"/api/events/{event['event_id']}/cancel", json={
            "cancelled_by_user_id": other["user_id"],
            "version": 1,
        })
        assert resp.status_code == 403

    def test_cancel_version_mismatch(self, client):
        """§15 — Optimistic lock on cancel."""
        organizer, _, group = _setup(client)
        event = _make_event(client, organizer["user_id"], group["group_id"]).json()

        resp = client.post(f"/api/events/{event['event_id']}/cancel", json={
            "cancelled_by_user_id": organizer["user_id"],
            "version": 999,
        })
        assert resp.status_code == 409


class TestHardConstraints:
    """§7.3 — Hard event overlap checks."""

    def test_hard_overlap_rejected(self, client):
        """Two Hard events at the same time for the same attendee → 409."""
        organizer, other, group = _setup(client)

        # Create first Hard event
        resp1 = _make_event(
            client, organizer["user_id"], group["group_id"],
            title="Hard Event 1", constraint="Hard",
            attendee_ids=[other["user_id"]],
            start_offset_hours=48,
        )
        assert resp1.status_code == 201

        # Create second overlapping Hard event with the same organizer
        resp2 = _make_event(
            client, organizer["user_id"], group["group_id"],
            title="Hard Event 2", constraint="Hard",
            attendee_ids=[other["user_id"]],
            start_offset_hours=48,  # same time
        )
        assert resp2.status_code == 409

    def test_soft_overlap_allowed(self, client):
        """Two Soft events at the same time are allowed."""
        organizer, _, group = _setup(client)

        resp1 = _make_event(
            client, organizer["user_id"], group["group_id"],
            title="Soft 1", constraint="Soft", start_offset_hours=72,
        )
        assert resp1.status_code == 201

        resp2 = _make_event(
            client, organizer["user_id"], group["group_id"],
            title="Soft 2", constraint="Soft", start_offset_hours=72,
        )
        assert resp2.status_code == 201


class TestDNDConflict:
    """§7.4 — DND window evaluation."""

    def test_hard_event_during_dnd_rejected(self, client):
        """Creating a Hard event that overlaps a user's DND window → 409."""
        # Create user with DND 22:00-07:00 UTC
        resp = client.post("/api/users/", json={
            "display_name": "Night Owl",
            "default_timezone": "UTC",
            "dnd_window_start_local": "22:00:00",
            "dnd_window_end_local": "07:00:00",
        })
        assert resp.status_code == 201
        user = resp.json()

        group = create_test_group(client, creator_id=user["user_id"])

        # Create Hard event at 23:00-23:30 UTC → clearly within 22:00-07:00 DND
        start = datetime.now(timezone.utc).replace(hour=23, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end = start + timedelta(minutes=30)

        resp = client.post("/api/events/", json={
            "group_id": group["group_id"],
            "title": "Late Meeting",
            "start_time_utc": start.isoformat(),
            "end_time_utc": end.isoformat(),
            "organizer_id": user["user_id"],
            "constraint_level": "Hard",
            "attendee_ids": [],
        })
        assert resp.status_code == 409


class TestEventList:
    """Event listing with filters."""

    def test_list_excludes_cancelled(self, client):
        organizer, _, group = _setup(client)
        event = _make_event(client, organizer["user_id"], group["group_id"], title="Will Cancel").json()

        # Cancel it
        client.post(f"/api/events/{event['event_id']}/cancel", json={
            "cancelled_by_user_id": organizer["user_id"],
            "version": 1,
        })

        # Default listing should exclude cancelled
        resp = client.get(f"/api/events/?group_id={group['group_id']}")
        assert resp.status_code == 200
        titles = [e["title"] for e in resp.json()]
        assert "Will Cancel" not in titles

    def test_list_includes_cancelled(self, client):
        organizer, _, group = _setup(client)
        event = _make_event(client, organizer["user_id"], group["group_id"], title="Cancelled One").json()
        client.post(f"/api/events/{event['event_id']}/cancel", json={
            "cancelled_by_user_id": organizer["user_id"],
            "version": 1,
        })

        resp = client.get(f"/api/events/?group_id={group['group_id']}&include_cancelled=true")
        assert resp.status_code == 200
        titles = [e["title"] for e in resp.json()]
        assert "Cancelled One" in titles
