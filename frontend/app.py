"""Smart Parking dashboard (Streamlit).  Run:  streamlit run frontend/app.py
The dashboard only talks to the REST API - it never touches the database directly.
Historical data shown in the demo is SYNTHETIC."""
import os
import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FREE, BUSY, ASPHALT, LINE = "#2E7D4F", "#B23A3A", "#2B3238", "#E8B931"
DEMAND_COLOR = {"Low": FREE, "Medium": "#C98A12", "High": BUSY}

st.set_page_config(page_title="Smart Parking", page_icon="🅿️", layout="wide")
st.markdown(f"""
<style>
.block-container {{padding-top: 1.6rem;}}
.kpi {{background:{ASPHALT}; color:#F5F6F4; border-radius:6px; padding:14px 18px; border-left:6px solid {LINE};}}
.kpi .v {{font-size:2.1rem; font-weight:700; line-height:1.1;}}
.kpi .l {{font-size:.9rem; opacity:.8;}}
.bays {{display:grid; grid-template-columns:repeat(auto-fill,minmax(112px,1fr)); gap:8px;}}
.bay {{border:2px solid {LINE}; border-radius:4px; padding:8px 8px 6px; color:#fff; min-height:74px; font-size:.78rem;}}
.bay b {{font-size:1.05rem; display:block;}}
.bay.free {{background:{FREE};}} .bay.busy {{background:{BUSY};}}
.badge {{display:inline-block; padding:6px 18px; border-radius:4px; color:#fff; font-size:1.5rem; font-weight:700;}}
@media (prefers-reduced-motion: reduce) {{* {{transition:none !important;}}}}
</style>""", unsafe_allow_html=True)


# ---------- API helpers ----------
def get(path: str, **params):
    try:
        r = requests.get(f"{API}{path}", params={k: v for k, v in params.items() if v not in (None, "")}, timeout=15)
        if r.ok:
            return r.json()
        st.error(f"API error {r.status_code}: {r.json().get('detail', r.text)}")
    except requests.RequestException:
        st.error(f"Cannot reach the API at {API}. Start it with:  uvicorn backend.main:app --reload")
    return None


def post(path: str, body: dict):
    try:
        r = requests.post(f"{API}{path}", json=body, timeout=15)
        return r.ok, r.json()
    except requests.RequestException:
        return False, {"detail": f"Cannot reach the API at {API}"}


def kpi(col, label, value):
    col.markdown(f'<div class="kpi"><div class="v">{value}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)


def style(fig, h=340):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.2))
    return fig


# ---------- sidebar ----------
st.sidebar.title("🅿️ Smart Parking")
page = st.sidebar.radio("Go to", ["Dashboard", "Live Parking", "Analytics", "AI Prediction", "Parking History"])
auto = st.sidebar.checkbox("Auto-refresh every 5 s", value=False)
st.sidebar.caption("Historical data is synthetic: it was generated for development and demonstration.")
st.sidebar.caption(f"API: {API}")


# ---------- pages ----------
def page_dashboard():
    st.title("Parking overview")
    s = get("/parking/status")
    if not s:
        return
    c = st.columns(4)
    kpi(c[0], "Total slots", s["total_slots"])
    kpi(c[1], "Available slots", s["available_slots"])
    kpi(c[2], "Occupied slots", s["occupied_slots"])
    kpi(c[3], "Occupancy", f'{s["occupancy_percent"]}%')
    st.write("")
    left, right = st.columns([1, 1])
    with left:
        fig = go.Figure(go.Pie(labels=["Available", "Occupied"], values=[s["available_slots"], s["occupied_slots"]],
                               hole=.6, marker_colors=[FREE, BUSY], sort=False))
        st.plotly_chart(style(fig, 300), width="stretch")
    with right:
        st.subheader("Record a vehicle")
        st.caption("Use these forms to demonstrate entry and exit live.")
        with st.form("entry"):
            plate = st.text_input("Vehicle number", placeholder="MH12AB1234")
            vtype = st.selectbox("Type", ["car", "bike", "truck"])
            if st.form_submit_button("Register entry"):
                ok, data = post("/parking/entry", {"vehicle_number": plate, "vehicle_type": vtype})
                if ok:
                    st.success(f'{data["vehicle_number"]} parked in {data["slot_number"]} (zone {data["zone"]}).')
                else:
                    st.error(data["detail"] if isinstance(data["detail"], str) else data["detail"][0]["msg"])
        with st.form("exit"):
            plate2 = st.text_input("Vehicle number leaving", placeholder="MH12AB1234")
            if st.form_submit_button("Register exit"):
                ok, data = post("/parking/exit", {"vehicle_number": plate2})
                if ok:
                    st.success(f'{data["vehicle_number"]} left {data["slot_number"]} after {data["duration_minutes"]} minutes.')
                else:
                    st.error(data["detail"] if isinstance(data["detail"], str) else data["detail"][0]["msg"])
    st.subheader("Latest activity")
    hist = get("/parking/history", limit=8)
    if hist:
        df = pd.DataFrame(hist)[["vehicle_number", "slot_number", "entry_time", "exit_time", "duration_minutes", "status"]]
        st.dataframe(df, width="stretch", hide_index=True)


def page_live():
    st.title("Live parking")
    slots = get("/parking/slots")
    if not slots:
        return
    zones = sorted({s["zone"] for s in slots})
    pick = st.multiselect("Zones", zones, default=zones)
    st.caption("Green = available, red = occupied.")
    for z in pick:
        st.subheader(f"Zone {z}")
        html = '<div class="bays">'
        for s in (x for x in slots if x["zone"] == z):
            free = s["status"] == "available"
            detail = "Available" if free else f'{s["vehicle_number"]}<br>since {str(s["since"])[11:16]}'
            html += f'<div class="bay {"free" if free else "busy"}"><b>{s["slot_number"]}</b>{detail}</div>'
        st.markdown(html + "</div>", unsafe_allow_html=True)


def page_analytics():
    st.title("Analytics")
    sm = get("/analytics/summary")
    if not sm:
        return
    c = st.columns(4)
    kpi(c[0], "Sessions recorded", sm["total_sessions"])
    kpi(c[1], "Average stay", f'{sm["avg_duration_minutes"]} min' if sm["avg_duration_minutes"] else "-")
    kpi(c[2], "Busiest hour", f'{sm["busiest_hour"]}:00' if sm["busiest_hour"] is not None else "-")
    kpi(c[3], "Quietest hour", f'{sm["quietest_hour"]}:00' if sm["quietest_hour"] is not None else "-")
    st.write("")
    days = st.slider("Days to show", 1, 30, 7)

    trend = get("/analytics/occupancy-trend", days=days)
    if trend:
        fig = px.area(pd.DataFrame(trend), x="timestamp", y="occupancy_pct", title="Occupancy over time (%)",
                      color_discrete_sequence=[ASPHALT])
        fig.update_yaxes(range=[0, 100])
        st.plotly_chart(style(fig), width="stretch")

    a, b = st.columns(2)
    daily = get("/analytics/daily", days=max(days, 7))
    if daily:
        d = pd.DataFrame(daily).melt("date", var_name="measure", value_name="occupancy_pct")
        a.plotly_chart(style(px.bar(d, x="date", y="occupancy_pct", color="measure", barmode="group",
                                    title="Daily occupancy (average and maximum %)",
                                    color_discrete_sequence=[ASPHALT, LINE])), width="stretch")
    ee = get("/analytics/entries-exits", days=max(days, 7))
    if ee:
        d = pd.DataFrame(ee).melt("date", var_name="event", value_name="vehicles")
        b.plotly_chart(style(px.bar(d, x="date", y="vehicles", color="event", barmode="group",
                                    title="Vehicle entries and exits per day",
                                    color_discrete_sequence=[FREE, BUSY])), width="stretch")

    a, b = st.columns(2)
    peak = get("/analytics/peak-hours", days=30)
    if peak:
        h = pd.DataFrame(peak["hourly"])
        h["kind"] = h["hour"].map(lambda x: "Peak" if x in peak["peak_hours"] else
                                  "Least busy" if x in peak["least_busy_hours"] else "Normal")
        fig = px.bar(h, x="hour", y="avg_occupancy_pct", color="kind", title="Average occupancy by hour (30 days)",
                     color_discrete_map={"Peak": BUSY, "Least busy": FREE, "Normal": "#9AA5AD"})
        a.plotly_chart(style(fig), width="stretch")
        a.caption(f'Peak hours: {", ".join(f"{x}:00" for x in peak["peak_hours"])} | '
                  f'Least busy: {", ".join(f"{x}:00" for x in peak["least_busy_hours"])}')
    wk = get("/analytics/weekly", days=28)
    if wk:
        w = pd.DataFrame(wk).pivot(index="day_of_week", columns="hour", values="avg_occupancy_pct")
        w.index = [DAYS[i] for i in w.index]
        fig = px.imshow(w, aspect="auto", color_continuous_scale="YlOrRd", title="Weekly pattern (avg occupancy %)",
                        labels=dict(x="Hour", y="", color="%"))
        b.plotly_chart(style(fig), width="stretch")

    hist = get("/parking/history", limit=2000, status="completed")
    if hist:
        dur = pd.DataFrame(hist)["duration_minutes"].dropna()
        st.plotly_chart(style(px.histogram(dur, nbins=40, title="Parking duration distribution (minutes, latest 2000 sessions)",
                                           color_discrete_sequence=[ASPHALT]).update_layout(showlegend=False)),
                        width="stretch")


def page_prediction():
    st.title("AI prediction")
    occ, dem = get("/prediction/occupancy"), get("/prediction/demand")
    if not occ or not dem:
        st.info("If the model is missing, train it with:  python -m ml.train")
        return
    c = st.columns(3)
    kpi(c[0], "Current occupancy", f'{occ["current_occupancy"]}%')
    kpi(c[1], "Predicted in 30 minutes", f'{occ["next_30_min"]}%')
    kpi(c[2], "Predicted in 60 minutes", f'{occ["next_60_min"]}%')
    st.write("")
    a, b = st.columns([1, 2])
    a.subheader("Expected demand")
    a.markdown(f'<span class="badge" style="background:{DEMAND_COLOR[dem["demand"]]}">{dem["demand"].upper()}</span>',
               unsafe_allow_html=True)
    a.caption(f'Model version {dem["model_version"]}')
    p = pd.DataFrame({"level": list(dem["probabilities"]), "probability": list(dem["probabilities"].values())})
    b.plotly_chart(style(px.bar(p, x="level", y="probability", title="How confident is the model?",
                                color="level", color_discrete_map=DEMAND_COLOR).update_yaxes(range=[0, 1])
                         .update_layout(showlegend=False), 260), width="stretch")

    st.subheader("How good is the model?")
    st.caption("Measured on a held-out test set of SYNTHETIC data; real-world performance may differ.")
    m = get("/prediction/model-info")
    if not m:
        return
    rows = []
    for h, r in m["regression"].items():
        rows.append({"Model": "Baseline (no change)", "Target": f"Occupancy in {h}", **r["baseline_no_change"]["test"]})
        rows += [{"Model": n + (" (selected)" if n == r["selected"] else ""), "Target": f"Occupancy in {h}", **v["test"]}
                 for n, v in r["models"].items()]
    st.markdown("**Occupancy prediction** (MAE/RMSE in percentage points, lower is better; R² closer to 1 is better)")
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    c = m["classification"]
    st.markdown(f'**Demand classification** ({c["rule"]})')
    st.dataframe(pd.DataFrame([{"Model": n + (" (selected)" if n == c["selected"] else ""), **v["test"]}
                               for n, v in c["models"].items()]), width="stretch", hide_index=True)
    cm = pd.DataFrame(c["models"][c["selected"]]["confusion_matrix"], index=c["labels"], columns=c["labels"])
    st.plotly_chart(style(px.imshow(cm, text_auto=True, color_continuous_scale="Blues",
                                    labels=dict(x="Predicted", y="Actual"),
                                    title=f'Confusion matrix - {c["selected"]}'), 320), width="stretch")


def page_history():
    st.title("Parking history")
    with st.expander("Filters", expanded=True):
        a, b, c, d = st.columns(4)
        vehicle = a.text_input("Vehicle number contains")
        slot = b.text_input("Slot (e.g. P05)")
        use_dates = c.checkbox("Filter by date")
        rng = c.date_input("Entry date range", value=(pd.Timestamp.now().date() - pd.Timedelta(days=7),
                                                       pd.Timestamp.now().date())) if use_dates else None
        status = d.selectbox("Status", ["", "parked", "completed"])
        e, f, g = st.columns(3)
        mn = e.number_input("Min duration (min)", min_value=0, value=0)
        mx = f.number_input("Max duration (min, 0 = any)", min_value=0, value=0)
        limit = g.number_input("Max rows", 10, 5000, 300)
    d_from = d_to = None
    if rng and len(rng) == 2:
        d_from, d_to = rng
    data = get("/parking/history", vehicle=vehicle, slot=slot, date_from=d_from, date_to=d_to,
               min_duration=mn or None, max_duration=mx or None, status=status, limit=limit)
    if data is None:
        return
    if not data:
        st.info("No sessions match these filters. Try widening them.")
        return
    df = pd.DataFrame(data)
    st.caption(f"{len(df)} sessions")
    st.dataframe(df, width="stretch", hide_index=True)
    st.download_button("Download CSV", df.to_csv(index=False), "parking_history.csv", "text/csv")


{"Dashboard": page_dashboard, "Live Parking": page_live, "Analytics": page_analytics,
 "AI Prediction": page_prediction, "Parking History": page_history}[page]()

if auto:
    time.sleep(5)
    st.rerun()
