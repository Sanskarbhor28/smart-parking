"""Pydantic schemas: validate what comes IN and shape what goes OUT."""
import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


def _clean_plate(value: str) -> str:
    plate = re.sub(r"[\s-]", "", value).upper()
    if not re.fullmatch(r"[A-Z0-9]{4,15}", plate):
        raise ValueError("vehicle_number must be 4-15 letters/digits (spaces and '-' are ignored)")
    return plate


class EntryRequest(BaseModel):
    vehicle_number: str
    vehicle_type: Literal["car", "bike", "truck"] = "car"
    slot_number: Optional[str] = None  # optional: request a specific slot

    _plate = field_validator("vehicle_number")(_clean_plate)


class ExitRequest(BaseModel):
    vehicle_number: str

    _plate = field_validator("vehicle_number")(_clean_plate)


class SessionOut(BaseModel):
    id: int
    vehicle_number: str
    vehicle_type: str
    slot_number: str
    zone: str
    entry_time: datetime
    exit_time: Optional[datetime]
    duration_minutes: Optional[float]
    status: Literal["parked", "completed"]


class SlotOut(BaseModel):
    slot_number: str
    zone: str
    status: str
    vehicle_number: Optional[str] = None
    since: Optional[datetime] = None


class StatusOut(BaseModel):
    total_slots: int
    available_slots: int
    occupied_slots: int
    occupancy_percent: float
    timestamp: datetime
