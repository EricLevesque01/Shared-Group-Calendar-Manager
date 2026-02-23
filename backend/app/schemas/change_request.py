"""Pydantic schemas for ChangeRequests."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class ChangeRequestCreate(BaseModel):
    event_id: str
    requester_id: str
    request_type: str  # time_change, cancel, update_details
    payload: dict[str, Any]


class ChangeRequestOut(BaseModel):
    request_id: str
    event_id: str
    requester_id: str
    request_type: str
    payload: dict[str, Any]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
