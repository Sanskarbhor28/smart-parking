"""Central configuration. All settings come from environment variables / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _abs(path_str: str) -> Path:
    """Make relative paths relative to the project root."""
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _db_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./data/smart_parking.db")
    if url.startswith("sqlite:///./"):
        return "sqlite:///" + str(_abs(url.replace("sqlite:///./", "")))
    return url


DATABASE_URL: str = _db_url()
TOTAL_SLOTS: int = int(os.getenv("TOTAL_SLOTS", "30"))
MODEL_DIR: Path = _abs(os.getenv("MODEL_DIR", "ml/models"))
DATA_DIR: Path = ROOT / "data"
API_URL: str = os.getenv("API_URL", "http://localhost:8000")

ZONES = 3  # slots are split evenly into zones A, B, C


def slot_layout(total: int = TOTAL_SLOTS) -> list[tuple[str, str]]:
    """Return [(slot_number, zone), ...]  e.g. ('P01', 'A').
    NOTE: ml/data_generator.py uses the same formula so synthetic data matches."""
    return [(f"P{i + 1:02d}", "ABC"[min(i * ZONES // total, ZONES - 1)]) for i in range(total)]
