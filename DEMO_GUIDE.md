# Demo guide (about 8-10 minutes)

Before the demo (do once, at home): follow the Quick start in `README.md` so the model is trained and the database is seeded.
Have 3 Command Prompt windows ready, each in the `smart-parking` folder with `venv\Scripts\activate` run.
Say early: **"The history is synthetic and the sensors are simulated."** Judges respect honesty.

| Step | Window | Command / action | What to say |
|---|---|---|---|
| 1 | A | `python -m database.seed_database --reset` | Loads 60 days of synthetic history into the database. |
| 2 | A | `uvicorn backend.main:app --reload` | This is the cloud API layer. |
| 3 | browser | `http://localhost:8000/docs` | Swagger: every endpoint is documented and testable. Try `GET /parking/status`. |
| 4 | B | `streamlit run frontend/app.py` | The dashboard only talks to the API. |
| 5 | browser | **Dashboard** page | KPI cards: total, available, occupied, occupancy %. |
| 6 | browser | Register an entry (e.g. `MH12AB1234`), then look at **Live Parking** | Slot P-number turns red; the API assigned the slot. |
| 7 | browser | Register the exit | Slot turns green; duration is calculated and stored. |
| 8 | C | `python -m simulator.parking_simulator --interval 1 --arrival-prob 0.7 --departure-prob 0.08 --seed 1` | The simulator acts as the IoT sensors. Enable **Auto-refresh** in the sidebar. |
| 9 | browser | **Analytics** | Occupancy trend, peak hours, weekly heatmap, entries vs exits. |
| 10 | browser | **AI Prediction** | Predicted occupancy at +30 and +60 min, demand level, and the model comparison with real metrics. Explain the baseline. |
| 11 | browser | **Parking History** | Filter by vehicle, slot, duration; download CSV. |
| 12 | slides | Cloud slide | Show `docs/AWS_DEPLOYMENT.md` design. Say clearly whether you actually deployed it. |

## Backup plan
- Dashboard says "Cannot reach the API" -> window A is not running.
- No predictions -> `python -m ml.train`.
- Empty analytics -> step 1.
- Wi-Fi is not needed; everything runs on the laptop.
