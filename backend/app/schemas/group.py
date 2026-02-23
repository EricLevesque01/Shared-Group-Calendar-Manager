"""Pydantic schemas for Groups."""
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class GroupCreate(BaseModel):
    name: str
    created_by: UUID


class GroupOut(BaseModel):
    group_id: UUID
    name: str
    created_by: UUID
    created_at: datetime
    members: list[GroupMemberOut] = []

    model_config = {"from_attributes": True}


class GroupMemberAdd(BaseModel):
    user_id: UUID
    role: str = "member"


class GroupMemberOut(BaseModel):
    user_id: UUID
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


# Rebuild GroupOut now that GroupMemberOut is defined
GroupOut.model_rebuild()
