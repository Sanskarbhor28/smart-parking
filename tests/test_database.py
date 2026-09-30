import pytest

from backend import crud
from backend.database import SessionLocal


def test_slots_created_on_startup(client):
    with SessionLocal() as db:
        assert crud.get_status(db)["total_slots"] == 5


def test_entry_exit_at_database_level(client):
    with SessionLocal() as db:
        s = crud.vehicle_entry(db, "MH12AB1234", "car")
        assert s.exit_time is None and s.slot.status == "occupied"
        s = crud.vehicle_exit(db, "MH12AB1234")
        assert s.duration_minutes is not None and s.slot.status == "available"


def test_business_rule_errors(client):
    with SessionLocal() as db:
        crud.vehicle_entry(db, "MH12AB1234")
        with pytest.raises(crud.ParkingError):
            crud.vehicle_entry(db, "MH12AB1234")
        with pytest.raises(crud.ParkingError):
            crud.vehicle_exit(db, "UNKNOWN99")


def test_sensor_data_written(client):
    from sqlalchemy import func, select
    from backend.models import SensorData
    with SessionLocal() as db:
        crud.vehicle_entry(db, "MH12AB1234")
        crud.vehicle_exit(db, "MH12AB1234")
        assert db.scalar(select(func.count(SensorData.id))) == 2
