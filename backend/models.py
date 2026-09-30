"""SQLAlchemy table definitions (see database/schema.sql for the plain SQL version)."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class ParkingSlot(Base):
    __tablename__ = "parking_slots"
    id: Mapped[int] = mapped_column(primary_key=True)
    slot_number: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    zone: Mapped[str] = mapped_column(String(5))
    status: Mapped[str] = mapped_column(String(15), default="available")  # available | occupied
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(15), default="car")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ParkingSession(Base):
    __tablename__ = "parking_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    slot_id: Mapped[int] = mapped_column(ForeignKey("parking_slots.id"))
    entry_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)

    vehicle: Mapped[Vehicle] = relationship()
    slot: Mapped[ParkingSlot] = relationship()

    __table_args__ = (Index("ix_sessions_vehicle_exit", "vehicle_id", "exit_time"),)


class SensorData(Base):
    __tablename__ = "sensor_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("parking_slots.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    occupancy_status: Mapped[str] = mapped_column(String(15))  # occupied | available


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    horizon_minutes: Mapped[int] = mapped_column(Integer)
    predicted_occupancy: Mapped[float] = mapped_column(Float)
    predicted_demand: Mapped[str] = mapped_column(String(10))
    model_version: Mapped[str] = mapped_column(String(40))
