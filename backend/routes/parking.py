from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import crud
from backend.database import get_db
from backend.schemas import EntryRequest, ExitRequest, SessionOut, SlotOut, StatusOut

router = APIRouter(prefix="/parking", tags=["Parking"])


@router.get("/status", response_model=StatusOut)
def status(db: Session = Depends(get_db)):
    """Total / available / occupied slots and occupancy %."""
    return crud.get_status(db)


@router.get("/slots", response_model=list[SlotOut])
def slots(db: Session = Depends(get_db)):
    """Status of every individual slot."""
    return crud.get_slots(db)


@router.post("/entry", response_model=SessionOut, status_code=201)
def entry(body: EntryRequest, db: Session = Depends(get_db)):
    """Vehicle enters: a free slot is assigned (or the requested one is used)."""
    return crud.session_to_dict(crud.vehicle_entry(db, body.vehicle_number, body.vehicle_type, body.slot_number))


@router.post("/exit", response_model=SessionOut)
def exit_(body: ExitRequest, db: Session = Depends(get_db)):
    """Vehicle leaves: slot is freed and the parking duration is stored."""
    return crud.session_to_dict(crud.vehicle_exit(db, body.vehicle_number))


@router.get("/history", response_model=list[SessionOut])
def history(vehicle: Optional[str] = None, slot: Optional[str] = None,
            date_from: Optional[date] = None, date_to: Optional[date] = None,
            min_duration: Optional[float] = Query(None, ge=0), max_duration: Optional[float] = Query(None, ge=0),
            status: Optional[Literal["parked", "completed"]] = None,
            limit: int = Query(200, ge=1, le=5000), offset: int = Query(0, ge=0),
            db: Session = Depends(get_db)):
    """Parking history with filters (newest first)."""
    return crud.get_history(db, vehicle, slot, date_from, date_to, min_duration, max_duration, status, limit, offset)
