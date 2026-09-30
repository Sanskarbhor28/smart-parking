# Changelog
## 2026-09-30 - Version 1.0.0
- Project scaffold, config via `.env`, SQLAlchemy models (SQLite + PostgreSQL capable)
- FastAPI endpoints: health, parking (status, slots, entry, exit, history), analytics (6), prediction (4)
- Synthetic data generator; ML training with model comparison, baseline, chronological split, saved models and metrics
- Parking sensor simulator (configurable interval, probabilities, seed)
- Streamlit dashboard (5 pages)
- 21 pytest tests (all passing on SQLite); dashboard pages run headlessly without exceptions
- Docker files, `database/schema.sql`, AWS guide (documented, untested)
- Documentation: README, PROJECT_REPORT, DEMO_GUIDE, VIVA_QUESTIONS
- Fixed: timestamp nanosecond warning in seeding (rounded to seconds); switched dashboard to `width="stretch"`
