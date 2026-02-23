"""Tests for ChangeRequest workflow — spec §10 (HITL model)."""
from datetime import datetime, timezone, timedelta
from tests.conftest import create_test_user, create_test_group


def _create_event_and_requester(client):
    """Helper — creates an organizer, requester, group, and event."""
    organizer = create_test_user(client, name="Organizer")
    requester = create_test_user(client, name="Requester")
    group = create_test_group(client, creator_id=organizer["user_id"])

    # Add requester to group
    client.post(f"/api/groups/{group['group_id']}/members", json={
        "user_id": requester["user_id"],
        "role": "member",
    })

    # Create event
    start = datetime.now(timezone.utc) + timedelta(hours=48)
    end = start + timedelta(hours=1)
    event_resp = client.post("/api/events/", json={
        "group_id": group["group_id"],
        "title": "Original Event",
        "start_time_utc": start.isoformat(),
        "end_time_utc": end.isoformat(),
        "organizer_id": organizer["user_id"],
        "attendee_ids": [requester["user_id"]],
    })
    assert event_resp.status_code == 201
    return organizer, requester, group, event_resp.json()


class TestChangeRequestWorkflow:
    """Create → Approve/Reject flow."""

    def test_create_change_request(self, client):
        """Non-organizer creates a change request → 201 (pending)."""
        _, requester, _, event = _create_event_and_requester(client)

        resp = client.post("/api/change-requests/", json={
            "event_id": event["event_id"],
            "requester_id": requester["user_id"],
            "request_type": "time_change",
            "payload": {"title": "Moved Dinner"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["request_type"] == "time_change"

    def test_approve_change_request(self, client):
        """Approving a CR applies the mutation to the event."""
        organizer, requester, _, event = _create_event_and_requester(client)

        # Create CR
        cr_resp = client.post("/api/change-requests/", json={
            "event_id": event["event_id"],
            "requester_id": requester["user_id"],
            "request_type": "update_details",
            "payload": {"title": "Approved Title Change"},
        })
        cr = cr_resp.json()

        # Approve
        resp = client.post(f"/api/change-requests/{cr['request_id']}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        # Verify the event was actually updated
        event_resp = client.get(f"/api/events/{event['event_id']}")
        assert event_resp.json()["title"] == "Approved Title Change"
        assert event_resp.json()["version"] == 2  # version incremented

    def test_reject_change_request(self, client):
        """Rejecting a CR sets status to rejected, event unchanged."""
        _, requester, _, event = _create_event_and_requester(client)

        cr_resp = client.post("/api/change-requests/", json={
            "event_id": event["event_id"],
            "requester_id": requester["user_id"],
            "request_type": "cancel",
            "payload": {"reason": "Don't want to go"},
        })
        cr = cr_resp.json()

        resp = client.post(f"/api/change-requests/{cr['request_id']}/reject")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

        # Event should still be active
        event_resp = client.get(f"/api/events/{event['event_id']}")
        assert event_resp.json()["status"] == "Proposed"

    def test_approve_already_approved(self, client):
        """Cannot approve an already-approved CR → 400."""
        _, requester, _, event = _create_event_and_requester(client)

        cr_resp = client.post("/api/change-requests/", json={
            "event_id": event["event_id"],
            "requester_id": requester["user_id"],
            "request_type": "update_details",
            "payload": {"title": "Double Approve"},
        })
        cr = cr_resp.json()

        # First approve
        client.post(f"/api/change-requests/{cr['request_id']}/approve")
        # Second approve
        resp = client.post(f"/api/change-requests/{cr['request_id']}/approve")
        assert resp.status_code == 400

    def test_list_change_requests(self, client):
        """List CRs filtered by event and status."""
        _, requester, _, event = _create_event_and_requester(client)

        # Create two CRs
        client.post("/api/change-requests/", json={
            "event_id": event["event_id"],
            "requester_id": requester["user_id"],
            "request_type": "time_change",
            "payload": {"title": "CR 1"},
        })
        client.post("/api/change-requests/", json={
            "event_id": event["event_id"],
            "requester_id": requester["user_id"],
            "request_type": "update_details",
            "payload": {"title": "CR 2"},
        })

        resp = client.get(f"/api/change-requests/?event_id={event['event_id']}")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2


class TestRSVP:
    """Attendee RSVP flow."""

    def test_rsvp(self, client):
        """Attendee can RSVP to an event."""
        _, requester, _, event = _create_event_and_requester(client)

        resp = client.post("/api/attendees/rsvp", json={
            "event_id": event["event_id"],
            "user_id": requester["user_id"],
            "rsvp_status": "going",
        })
        assert resp.status_code == 200
        assert resp.json()["rsvp_status"] == "going"

    def test_rsvp_invalid_status(self, client):
        """Invalid RSVP status → 400."""
        _, requester, _, event = _create_event_and_requester(client)

        resp = client.post("/api/attendees/rsvp", json={
            "event_id": event["event_id"],
            "user_id": requester["user_id"],
            "rsvp_status": "not_a_status",
        })
        assert resp.status_code == 400

    def test_rsvp_non_attendee(self, client):
        """Non-attendee user RSVP → 404."""
        organizer = create_test_user(client, name="Organizer")
        outsider = create_test_user(client, name="Outsider")
        group = create_test_group(client, creator_id=organizer["user_id"])

        start = datetime.now(timezone.utc) + timedelta(hours=48)
        end = start + timedelta(hours=1)
        event = client.post("/api/events/", json={
            "group_id": group["group_id"],
            "title": "Private Event",
            "start_time_utc": start.isoformat(),
            "end_time_utc": end.isoformat(),
            "organizer_id": organizer["user_id"],
            "attendee_ids": [],
        }).json()

        resp = client.post("/api/attendees/rsvp", json={
            "event_id": event["event_id"],
            "user_id": outsider["user_id"],
            "rsvp_status": "going",
        })
        assert resp.status_code == 404
