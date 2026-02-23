"""Tests for User CRUD endpoints."""
from tests.conftest import create_test_user


class TestUserCRUD:
    """User create / get / update / list."""

    def test_create_user(self, client):
        data = create_test_user(client, name="Alice", tz="US/Eastern")
        assert data["display_name"] == "Alice"
        assert data["default_timezone"] == "US/Eastern"
        assert "user_id" in data

    def test_get_user(self, client):
        user = create_test_user(client)
        resp = client.get(f"/api/users/{user['user_id']}")
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Test User"

    def test_get_user_not_found(self, client):
        resp = client.get("/api/users/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_update_user(self, client):
        user = create_test_user(client)
        resp = client.patch(f"/api/users/{user['user_id']}", json={
            "display_name": "Updated Name",
            "default_timezone": "Europe/London",
        })
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated Name"
        assert resp.json()["default_timezone"] == "Europe/London"

    def test_list_users(self, client):
        create_test_user(client, name="Alice")
        create_test_user(client, name="Bob")
        resp = client.get("/api/users/")
        assert resp.status_code == 200
        users = resp.json()
        assert len(users) >= 2
        names = [u["display_name"] for u in users]
        assert "Alice" in names
        assert "Bob" in names

    def test_create_user_with_dnd(self, client):
        resp = client.post("/api/users/", json={
            "display_name": "Night Owl",
            "default_timezone": "US/Eastern",
            "dnd_window_start_local": "22:00:00",
            "dnd_window_end_local": "07:00:00",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["dnd_window_start_local"] == "22:00:00"
        assert data["dnd_window_end_local"] == "07:00:00"
