"""Database engine/session setup. Works with SQLite (local) and PostgreSQL (cloud)."""
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend import config


class Base(DeclarativeBase):
    pass


_is_sqlite = config.DATABASE_URL.startswith("sqlite")
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    """FastAPI dependency: one DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables and make sure the parking slots exist."""
    from backend import models  # noqa: F401  (registers tables)

    config.DATA_DIR.mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        existing = set(db.scalars(select(models.ParkingSlot.slot_number)))
        for number, zone in config.slot_layout():
            if number not in existing:
                db.add(models.ParkingSlot(slot_number=number, zone=zone, status="available"))
        db.commit()
