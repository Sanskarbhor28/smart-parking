"""FastAPI application.  Run:  uvicorn backend.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.crud import ParkingError
from backend.database import init_db
from backend.routes import analytics, health, parking, prediction


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables + slots on startup
    yield


app = FastAPI(
    title="Smart Parking API",
    description="Cloud-based smart parking management with AI prediction. "
                "Historical data in the demo database is SYNTHETIC.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ParkingError)
async def parking_error_handler(request: Request, exc: ParkingError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


for r in (health.router, parking.router, analytics.router, prediction.router):
    app.include_router(r)
