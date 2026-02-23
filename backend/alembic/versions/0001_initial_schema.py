"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-02-23

Creates all tables for the Shared Group Calendar application:
users, groups, group_members, events, event_attendees,
change_requests, event_mutations.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(36), primary_key=True),
        sa.Column("display_name", sa.String(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False, server_default=""),
        sa.Column("default_timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("dnd_window_start_local", sa.Time, nullable=True),
        sa.Column("dnd_window_end_local", sa.Time, nullable=True),
        sa.Column("aliases", sa.JSON, nullable=True),
        sa.Column("enable_transit_checks", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- groups ---
    op.create_table(
        "groups",
        sa.Column("group_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- group_members ---
    op.create_table(
        "group_members",
        sa.Column("group_id", sa.String(36), sa.ForeignKey("groups.group_id"), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.user_id"), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- events ---
    op.create_table(
        "events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("groups.group_id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("start_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organizer_id", sa.String(36), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="Proposed"),
        sa.Column("constraint_level", sa.String(10), nullable=False, server_default="Soft"),
        sa.Column("event_type", sa.String(20), nullable=False, server_default="default"),
        sa.Column("location_type", sa.String(20), nullable=True),
        sa.Column("location_text", sa.String(500), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_user_id", sa.String(36), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("cancel_reason", sa.String(500), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- event_attendees ---
    op.create_table(
        "event_attendees",
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.event_id"), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.user_id"), primary_key=True),
        sa.Column("rsvp_status", sa.String(20), nullable=False, server_default="invited"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- change_requests ---
    op.create_table(
        "change_requests",
        sa.Column("request_id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.event_id"), nullable=False),
        sa.Column("requester_id", sa.String(36), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("request_type", sa.String(30), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- event_mutations ---
    op.create_table(
        "event_mutations",
        sa.Column("mutation_id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.event_id"), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("action_type", sa.String(20), nullable=False),
        sa.Column("before_snapshot", sa.JSON, nullable=True),
        sa.Column("after_snapshot", sa.JSON, nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("event_mutations")
    op.drop_table("change_requests")
    op.drop_table("event_attendees")
    op.drop_table("events")
    op.drop_table("group_members")
    op.drop_table("groups")
    op.drop_table("users")
