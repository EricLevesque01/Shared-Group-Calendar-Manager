"""Tests for Group CRUD and membership endpoints."""
from tests.conftest import create_test_user, create_test_group


class TestGroupCRUD:
    """Group create / get / list / members."""

    def test_create_group(self, client):
        user = create_test_user(client, name="Admin")
        group = create_test_group(client, creator_id=user["user_id"], name="Movie Night Crew")
        assert group["name"] == "Movie Night Crew"
        assert group["created_by"] == user["user_id"]
        # Creator should be auto-added as admin
        assert len(group["members"]) == 1
        assert group["members"][0]["role"] == "admin"

    def test_get_group(self, client):
        user = create_test_user(client)
        group = create_test_group(client, creator_id=user["user_id"])
        resp = client.get(f"/api/groups/{group['group_id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Group"

    def test_get_group_not_found(self, client):
        resp = client.get("/api/groups/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_add_member(self, client):
        admin = create_test_user(client, name="Admin")
        member = create_test_user(client, name="Member")
        group = create_test_group(client, creator_id=admin["user_id"])

        resp = client.post(f"/api/groups/{group['group_id']}/members", json={
            "user_id": member["user_id"],
            "role": "member",
        })
        assert resp.status_code == 201
        assert resp.json()["role"] == "member"

    def test_add_duplicate_member(self, client):
        """§ Duplicate membership → 409."""
        admin = create_test_user(client, name="Admin")
        group = create_test_group(client, creator_id=admin["user_id"])

        # Admin is already a member; try to add again
        resp = client.post(f"/api/groups/{group['group_id']}/members", json={
            "user_id": admin["user_id"],
            "role": "member",
        })
        assert resp.status_code == 409

    def test_remove_member(self, client):
        admin = create_test_user(client, name="Admin")
        member = create_test_user(client, name="Member")
        group = create_test_group(client, creator_id=admin["user_id"])

        # Add then remove
        client.post(f"/api/groups/{group['group_id']}/members", json={
            "user_id": member["user_id"],
            "role": "member",
        })
        resp = client.delete(f"/api/groups/{group['group_id']}/members/{member['user_id']}")
        assert resp.status_code == 204

    def test_list_groups(self, client):
        user = create_test_user(client)
        create_test_group(client, creator_id=user["user_id"], name="Group A")
        create_test_group(client, creator_id=user["user_id"], name="Group B")
        resp = client.get("/api/groups/")
        assert resp.status_code == 200
        names = [g["name"] for g in resp.json()]
        assert "Group A" in names
        assert "Group B" in names
