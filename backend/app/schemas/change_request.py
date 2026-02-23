"""Pydantic schemas for ChangeRequests."""
from datetime import datetime
from uuid import UUID
from typing import Optional, Any
from pydantic import BaseModel


class ChangeRequestCreate(BaseModel):
    event_id: UUID
    requester_id: UUID
    request_type: str  # time_change, cancel, update_details
    payload: dict[str, Any]


class ChangeRequestOut(BaseModel):
    request_id: UUID
    event_id: UUID
    requester_id: UUID
    request_type: str
    payload: dict[str, Any]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
