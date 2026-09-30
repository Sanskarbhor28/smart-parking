-- PostgreSQL schema for the Smart Parking system.
-- The app also creates these tables automatically through SQLAlchemy (backend/models.py);
-- use this file if you want to create them by hand:  psql -f database/schema.sql
-- NOTE: written for PostgreSQL; the automatic SQLAlchemy route is what was tested (on SQLite).

CREATE TABLE IF NOT EXISTS parking_slots (
    id          SERIAL PRIMARY KEY,
    slot_number VARCHAR(10) NOT NULL UNIQUE,
    zone        VARCHAR(5)  NOT NULL,
    status      VARCHAR(15) NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'occupied')),
    updated_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vehicles (
    id             SERIAL PRIMARY KEY,
    vehicle_number VARCHAR(20) NOT NULL UNIQUE,
    vehicle_type   VARCHAR(15) NOT NULL DEFAULT 'car',
    created_at     TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS parking_sessions (
    id               SERIAL PRIMARY KEY,
    vehicle_id       INTEGER   NOT NULL REFERENCES vehicles(id),
    slot_id          INTEGER   NOT NULL REFERENCES parking_slots(id),
    entry_time       TIMESTAMP NOT NULL,
    exit_time        TIMESTAMP,              -- NULL while the vehicle is still parked
    duration_minutes DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS ix_parking_sessions_entry_time ON parking_sessions(entry_time);
CREATE INDEX IF NOT EXISTS ix_parking_sessions_exit_time  ON parking_sessions(exit_time);
CREATE INDEX IF NOT EXISTS ix_sessions_vehicle_exit       ON parking_sessions(vehicle_id, exit_time);

CREATE TABLE IF NOT EXISTS sensor_data (
    id               SERIAL PRIMARY KEY,
    slot_id          INTEGER     NOT NULL REFERENCES parking_slots(id),
    timestamp        TIMESTAMP   NOT NULL,
    occupancy_status VARCHAR(15) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sensor_data_slot_id   ON sensor_data(slot_id);
CREATE INDEX IF NOT EXISTS ix_sensor_data_timestamp ON sensor_data(timestamp);

CREATE TABLE IF NOT EXISTS predictions (
    id                  SERIAL PRIMARY KEY,
    prediction_time     TIMESTAMP        NOT NULL DEFAULT NOW(),
    horizon_minutes     INTEGER          NOT NULL,
    predicted_occupancy DOUBLE PRECISION NOT NULL,
    predicted_demand    VARCHAR(10)      NOT NULL,
    model_version       VARCHAR(40)      NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_predictions_time ON predictions(prediction_time);

-- ---------- Useful queries ----------
-- Current occupancy:
--   SELECT COUNT(*) FILTER (WHERE status='occupied') AS occupied, COUNT(*) AS total FROM parking_slots;
-- Average stay (minutes):
--   SELECT ROUND(AVG(duration_minutes)::numeric, 1) FROM parking_sessions WHERE exit_time IS NOT NULL;
-- Entries per hour of day (peak hours):
--   SELECT EXTRACT(HOUR FROM entry_time) AS hour, COUNT(*) FROM parking_sessions GROUP BY 1 ORDER BY 2 DESC;
-- Vehicles parked right now:
--   SELECT v.vehicle_number, s.slot_number, p.entry_time FROM parking_sessions p
--   JOIN vehicles v ON v.id = p.vehicle_id JOIN parking_slots s ON s.id = p.slot_id WHERE p.exit_time IS NULL;
