"""Database operations + parking business rules."""
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import ParkingSession, ParkingSlot, SensorData, Vehicle


class ParkingError(Exception):
    """A business-rule problem. `status_code` is the HTTP code the API should return."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------- status ----------
def get_status(db: Session) -> dict:
    total = db.scalar(select(func.count(ParkingSlot.id))) or 0
    occupied = db.scalar(select(func.count(ParkingSlot.id)).where(ParkingSlot.status == "occupied")) or 0
    return {
        "total_slots": total,
        "available_slots": total - occupied,
        "occupied_slots": occupied,
        "occupancy_percent": round(occupied / total * 100, 1) if total else 0.0,
        "timestamp": datetime.now(),
    }


def get_slots(db: Session) -> list[dict]:
    """Every slot, plus the vehicle currently in it (if any)."""
    active = {
        s.slot_id: s
        for s in db.scalars(select(ParkingSession).where(ParkingSession.exit_time.is_(None)))
    }
    out = []
    for slot in db.scalars(select(ParkingSlot).order_by(ParkingSlot.slot_number)):
        sess = active.get(slot.id)
        out.append({
            "slot_number": slot.slot_number,
            "zone": slot.zone,
            "status": slot.status,
            "vehicle_number": sess.vehicle.vehicle_number if sess else None,
            "since": sess.entry_time if sess else None,
        })
    return out


# ---------- entry / exit ----------
def vehicle_entry(db: Session, vehicle_number: str, vehicle_type: str = "car",
                  slot_number: Optional[str] = None) -> ParkingSession:
    vehicle = db.scalar(select(Vehicle).where(Vehicle.vehicle_number == vehicle_number))
    if vehicle:
        already = db.scalar(select(ParkingSession).where(
            ParkingSession.vehicle_id == vehicle.id, ParkingSession.exit_time.is_(None)))
        if already:
            raise ParkingError(f"Vehicle {vehicle_number} is already parked in {already.slot.slot_number}", 409)
    else:
        vehicle = Vehicle(vehicle_number=vehicle_number, vehicle_type=vehicle_type)
        db.add(vehicle)
        db.flush()

    if slot_number:
        slot = db.scalar(select(ParkingSlot).where(ParkingSlot.slot_number == slot_number.upper()))
        if not slot:
            raise ParkingError(f"Slot {slot_number} does not exist", 404)
        if slot.status != "available":
            raise ParkingError(f"Slot {slot.slot_number} is already occupied", 409)
    else:
        slot = db.scalar(select(ParkingSlot).where(ParkingSlot.status == "available")
                         .order_by(ParkingSlot.slot_number).limit(1))
        if not slot:
            raise ParkingError("Parking is full - no slots available", 409)

    now = datetime.now()
    slot.status = "occupied"
    session = ParkingSession(vehicle_id=vehicle.id, slot_id=slot.id, entry_time=now)
    db.add(session)
    db.add(SensorData(slot_id=slot.id, timestamp=now, occupancy_status="occupied"))
    db.commit()
    return session


def vehicle_exit(db: Session, vehicle_number: str) -> ParkingSession:
    vehicle = db.scalar(select(Vehicle).where(Vehicle.vehicle_number == vehicle_number))
    session = None
    if vehicle:
        session = db.scalar(select(ParkingSession).where(
            ParkingSession.vehicle_id == vehicle.id, ParkingSession.exit_time.is_(None)))
    if not session:
        raise ParkingError(f"No active parking session for vehicle {vehicle_number}", 404)

    now = datetime.now()
    session.exit_time = now
    session.duration_minutes = round((now - session.entry_time).total_seconds() / 60, 2)
    session.slot.status = "available"
    db.add(SensorData(slot_id=session.slot_id, timestamp=now, occupancy_status="available"))
    db.commit()
    return session


# ---------- history ----------
def session_to_dict(s: ParkingSession) -> dict:
    return {
        "id": s.id,
        "vehicle_number": s.vehicle.vehicle_number,
        "vehicle_type": s.vehicle.vehicle_type,
        "slot_number": s.slot.slot_number,
        "zone": s.slot.zone,
        "entry_time": s.entry_time,
        "exit_time": s.exit_time,
        "duration_minutes": s.duration_minutes,
        "status": "parked" if s.exit_time is None else "completed",
    }


def get_history(db: Session, vehicle: Optional[str] = None, slot: Optional[str] = None,
                date_from: Optional[date] = None, date_to: Optional[date] = None,
                min_duration: Optional[float] = None, max_duration: Optional[float] = None,
                status: Optional[str] = None, limit: int = 200, offset: int = 0) -> list[dict]:
    q = (select(ParkingSession).join(Vehicle).join(ParkingSlot)
         .order_by(ParkingSession.entry_time.desc()))
    if vehicle:
        q = q.where(Vehicle.vehicle_number.contains(vehicle.upper().replace(" ", "")))
    if slot:
        q = q.where(ParkingSlot.slot_number == slot.upper())
    if date_from:
        q = q.where(ParkingSession.entry_time >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.where(ParkingSession.entry_time < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    if min_duration is not None:
        q = q.where(ParkingSession.duration_minutes >= min_duration)
    if max_duration is not None:
        q = q.where(ParkingSession.duration_minutes <= max_duration)
    if status == "parked":
        q = q.where(ParkingSession.exit_time.is_(None))
    elif status == "completed":
        q = q.where(ParkingSession.exit_time.is_not(None))
    q = q.limit(limit).offset(offset)
    return [session_to_dict(s) for s in db.scalars(q)]
