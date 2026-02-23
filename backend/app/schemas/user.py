"""Pydantic schemas for Users."""
from __future__ import annotations
from datetime import datetime, time
from typing import Optional
from pydantic import BaseModel


class UserCreate(BaseModel):
    display_name: str
    default_timezone: str = "UTC"
    dnd_window_start_local: Optional[time] = None
    dnd_window_end_local: Optional[time] = None
    aliases: Optional[list[str]] = None
    enable_transit_checks: bool = False


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    default_timezone: Optional[str] = None
    dnd_window_start_local: Optional[time] = None
    dnd_window_end_local: Optional[time] = None
    aliases: Optional[list[str]] = None
    enable_transit_checks: Optional[bool] = None


class UserOut(BaseModel):
    user_id: str
    display_name: str
    default_timezone: str
    dnd_window_start_local: Optional[time] = None
    dnd_window_end_local: Optional[time] = None
    aliases: Optional[list[str]] = None
    enable_transit_checks: bool
    created_at: datetime

    model_config = {"from_attributes": True}
