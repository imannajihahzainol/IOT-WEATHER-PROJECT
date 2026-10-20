import csv
import os
import sqlite3
from datetime import datetime, timezone

import requests

LAT, LON = 4.3667, 100.9833
DB_FILE = "weather.db"
URL = "https://api.open-meteo.com/v1/forecast"
PARAMS = {
    "latitude": LAT,
    "longitude": LON,
    "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
    "hourly": "temperature_2m,relative_humidity_2m,precipitation,"
              "precipitation_probability,wind_speed_10m",
    "forecast_days": 3,
    "timezone": "UTC",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    obs_time      TEXT PRIMARY KEY,   -- UTC, e.g. 2026-10-20T08:15
    temperature   REAL,               -- deg C
    humidity      REAL,               -- %
    precipitation REAL,               -- mm
    wind_speed    REAL                -- km/h
);
CREATE TABLE IF NOT EXISTS forecasts (
    fetched_at    TEXT,               -- when we asked the API (UTC, on the hour)
    target_time   TEXT,               -- hour being predicted (UTC)
    lead_hours    INTEGER,            -- target_time minus fetched_at
    temperature   REAL,
    humidity      REAL,
    precipitation REAL,
    precip_prob   REAL,               -- %
    wind_speed    REAL,
    PRIMARY KEY (fetched_at, target_time)
);
CREATE TABLE IF NOT EXISTS collector_log (
    run_time TEXT,
    status   TEXT,                    -- OK or ERROR
    message  TEXT
);
"""


def log(conn, status, message):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    conn.execute("INSERT INTO collector_log VALUES (?,?,?)", (now, status, message))
    conn.commit()


def export_csv(conn):
    os.makedirs("data", exist_ok=True)
    for table in ("observations", "forecasts", "collector_log"):
        cur = conn.execute(f"SELECT * FROM {table}")
        with open(f"data/{table}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([c[0] for c in cur.description])
            w.writerows(cur.fetchall())


def main():
    conn = sqlite3.connect(DB_FILE)
    conn.executescript(SCHEMA)
    try:
        r = requests.get(URL, params=PARAMS, timeout=30)
        r.raise_for_status()
        data = r.json()

        # 1. Observation (the "actual" values)
        cur = data["current"]
        conn.execute(
            "INSERT OR REPLACE INTO observations VALUES (?,?,?,?,?)",
            (cur["time"], cur["temperature_2m"], cur["relative_humidity_2m"],
             cur["precipitation"], cur["wind_speed_10m"]),
        )

        # 2. Forecast snapshot, one row per future hour
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        fetched_at = now.strftime("%Y-%m-%dT%H:%M")
        h = data["hourly"]
        n = 0
        for i, t in enumerate(h["time"]):
            target = datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
            lead = int((target - now).total_seconds() // 3600)
            if lead < 0:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO forecasts VALUES (?,?,?,?,?,?,?,?)",
                (fetched_at, t, lead, h["temperature_2m"][i],
                 h["relative_humidity_2m"][i], h["precipitation"][i],
                 h["precipitation_probability"][i], h["wind_speed_10m"][i]),
            )
            n += 1
        conn.commit()
        log(conn, "OK", f"1 observation, {n} forecast rows")
        print(f"OK: 1 observation row(s), {n} forecast row(s)")
    except Exception as e:
        log(conn, "ERROR", str(e))
        print("ERROR:", e)
        raise
    finally:
        export_csv(conn)
        conn.close()


if __name__ == "__main__":
    main()
