from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Is the API up and can it reach the database?"""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected", "time": datetime.now()}
