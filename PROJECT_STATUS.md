Project: Cloud-Based Smart Parking Management and AI Prediction System
Current Phase: All build phases complete (v1.0.0). Remaining work is on the student's machine.
Status: Working locally (SQLite). Tested here.
Completed: Backend API, database models, simulator, synthetic data, ML training + evaluation, Streamlit dashboard (5 pages),
           21 pytest tests, Docker files, SQL schema, README, PROJECT_REPORT, DEMO_GUIDE, VIVA_QUESTIONS, AWS guide
In Progress: -
Next (student): run on Windows 11; take screenshots into docs/screenshots/; try PostgreSQL via docker compose;
                optionally deploy to AWS following docs/AWS_DEPLOYMENT.md and then update this file with what really happened
Known Issues / NOT verified:
  - PostgreSQL, Docker and AWS were NOT executed (no such environment); only SQLite was tested
  - Not run on Windows 11 (built and tested on Linux, Python 3.12)
  - Dashboard visuals were not viewed in a real browser; pages were executed headlessly (no exceptions)
  - Data is synthetic; ML metrics apply to synthetic data only; they vary slightly between training runs
  - No authentication / HTTPS
Environment: Python 3.11+ (tested on 3.12), venv, requirements.txt
Database: SQLite default; PostgreSQL via DATABASE_URL (untested)
Cloud: Design + guide only (EC2 + RDS). Not deployed.
AI Model: Random Forest selected for +30/+60 min occupancy and demand (see ml/models/metrics.json after training)
Frontend: Streamlit, frontend/app.py
Backend: FastAPI, backend/main.py
Deployment: Not deployed
Last Updated: 2026-09-30
