# Project Report: Cloud-Based Smart Parking Management and AI Prediction System

> Data note: **Synthetic data is used for development and demonstration.** All parking history and every ML result below come from
> synthetic data, so they show that the pipeline works, not how it would perform in a real car park.

## 1. Introduction
Finding a free parking slot wastes time and fuel, and operators rarely have usable data about how their car park is used.
This project builds a working system that records parking events, stores them centrally, analyses usage and predicts near-future
occupancy and demand, shown on a web dashboard.

## 2. Problem Statement
Drivers cannot know in advance whether a slot will be free, and operators lack data-driven insight into peak times and durations.
Manual or stand-alone systems show only the current state and do not predict future demand.

## 3. Objectives
1. Design a relational database for slots, vehicles, sessions, sensor readings and predictions.
2. Build a REST API for entry, exit, status, history, analytics and predictions.
3. Simulate parking sensors that send events to the API.
4. Train and compare ML models for occupancy (regression) and demand level (classification).
5. Present everything in a Streamlit dashboard.
6. Prepare a cloud-ready deployment (AWS) with documentation.

## 4. Existing System
Typical small car parks use manual ticketing or simple counters. Some smart systems show live availability but do not analyse history
or forecast demand. (This is a general description; no specific product is evaluated in this project.)

## 5. Proposed System
Parking events go to a FastAPI service, which stores them in a relational database. A saved ML model predicts occupancy 30 and 60
minutes ahead and classifies demand as Low, Medium or High. A Streamlit dashboard shows live status, analytics, predictions and history.

## 6. Architecture
Simulator (IoT stand-in) -> FastAPI -> SQLite (local) / PostgreSQL (cloud design) -> ML model loaded from disk -> Streamlit (via API).
The dashboard never accesses the database directly. See `README.md` and `docs/ER_DIAGRAM.md`.

## 7. Technology Stack
Python 3, FastAPI + Uvicorn, SQLAlchemy 2 + Pydantic, SQLite / PostgreSQL, Pandas, NumPy, scikit-learn, Plotly, Streamlit,
pytest, Docker (files provided), AWS EC2 + RDS (design only).

## 8. Database Design
Five tables: `parking_slots`, `vehicles`, `parking_sessions` (FKs to vehicles and slots; `exit_time` NULL while parked),
`sensor_data` (FK to slots; written on each entry and exit) and `predictions`. Indexes on entry/exit time, timestamps and slot ids.
See `database/schema.sql` and `docs/ER_DIAGRAM.md`.

## 9. AI/ML Methodology
- **Dataset:** 2826 time-steps of 30 minutes built from 60 days of synthetic parking sessions
  (train 1978 / validation 424 / test 424, split in time order so the model is tested on later data than it was trained on).
- **Features:** hour_float, day_of_week, is_weekend, occupancy_pct, occ_lag_30, occ_change, arrivals_30, departures_30.
- **Targets:** occupancy % 30 and 60 minutes ahead; demand level from the 60-minute occupancy (Low < 40% <= Medium < 70% <= High (occupancy in 60 min)).
- **Models:** Linear Regression and Random Forest (regression); Logistic Regression and Random Forest (classification).
  A "no change" baseline (predict current occupancy) is included to show whether the models add value.
- **Selection:** best model on the validation set; final numbers reported on the untouched test set; the winner is then re-fitted on train + validation and saved.
- **Limitation of the label:** the demand label is defined by a fixed occupancy rule, so it is a classification of a future occupancy band, not customer-reported demand.

## 10. Implementation
Backend in `backend/` (routes, business rules in `crud.py`, analytics in `analytics.py`), ML in `ml/`, simulator in `simulator/parking_simulator.py`,
dashboard in `frontend/app.py`, seed script in `database/seed_database.py`. Feature engineering is shared by training, live prediction and analytics
so the model always sees identically built inputs.

## 11. Results
Actual results from the saved run (model version `v20260930-0513`), measured on the test set of synthetic data.
Because the data is regenerated on each training run, your numbers will differ slightly.

**Occupancy prediction** (MAE and RMSE are in percentage points of occupancy; lower is better. R² near 1 is better):

| Target | Model | MAE | RMSE | R² |
|---|---|---|---|---|
| Occupancy in 30min | Baseline (no change) | 7.115 | 10.24 | 0.8944 |
| Occupancy in 30min | Linear Regression | 6.597 | 8.838 | 0.9213 |
| Occupancy in 30min | Random Forest **(selected)** | 5.773 | 7.753 | 0.9395 |
| Occupancy in 60min | Baseline (no change) | 12.099 | 16.833 | 0.7149 |
| Occupancy in 60min | Linear Regression | 10.719 | 13.933 | 0.8047 |
| Occupancy in 60min | Random Forest **(selected)** | 7.309 | 9.926 | 0.9009 |

**Demand classification:**

| Model | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| Logistic Regression | 0.8255 | 0.8113 | 0.8099 | 0.8102 |
| Random Forest **(selected)** | 0.8585 | 0.8451 | 0.8489 | 0.8467 |

Confusion matrix of Random Forest (rows = actual, columns = predicted):

| | Pred Low | Pred Medium | Pred High |
|---|---|---|---|
| Actual Low | 167 | 17 | 0 |
| Actual Medium | 10 | 88 | 20 |
| Actual High | 1 | 12 | 109 |

How to read this: MAE is the average size of the error; RMSE punishes large errors more; R² is the share of variation explained.
Accuracy is the share of correct classes; precision/recall/F1 are macro-averaged over the three classes.
Where the "no change" baseline is close to a model, the model adds little at that horizon; the gap is largest at 60 minutes.
Screenshots of the dashboard should be added by the student (placeholder: `docs/screenshots/`).

## 12. Testing
21 automated tests (pytest) cover: health, slot status, entry, exit, duplicate entry, full lot, unknown vehicle, validation errors, history filters,
database operations and sensor rows, analytics endpoints, prediction endpoints, feature engineering and model metrics. All 21 passed on SQLite.
The five dashboard pages were run headlessly with Streamlit's test runner against the live API with no exceptions. The simulator was run against the live API.
Not tested: PostgreSQL, Docker, AWS, and dashboard behaviour in a real browser beyond server start-up.

## 13. Cloud Deployment
Cloud-ready by design (environment-based config, PostgreSQL support, Docker files). `docs/AWS_DEPLOYMENT.md` gives an EC2 + RDS procedure with cost warnings.
**It has not been deployed by the author of the code; no deployment result is claimed.**

## 14. Advantages
Runs without hardware or AWS credentials; modular; understandable ML; honest evaluation with baseline; automated tests.

## 15. Limitations
Synthetic data only; a single lot; no authentication; no payment; timestamps use server local time; the simulator uses real time rather than accelerated time;
predictions reflect patterns built into the synthetic generator; PostgreSQL/Docker/AWS untested.

## 16. Future Scope
Real IoT sensors (for example via MQTT / AWS IoT Core), camera-based number-plate detection, user login, HTTPS, retraining on real data,
time-series models, mobile app, dynamic pricing. (None of these are implemented.)

## 17. Conclusion
The project delivers a working end-to-end pipeline: events, API, database, ML, analytics and dashboard, with measured results on synthetic data
and clearly stated limitations.

## 18. References
No academic references are fabricated here. Add the documentation you actually used, for example: FastAPI documentation (fastapi.tiangolo.com),
SQLAlchemy documentation (sqlalchemy.org), scikit-learn documentation (scikit-learn.org), Streamlit documentation (docs.streamlit.io),
PostgreSQL documentation (postgresql.org/docs), AWS documentation (docs.aws.amazon.com), plus any papers you read yourself.
