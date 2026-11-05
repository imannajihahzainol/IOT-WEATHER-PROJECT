
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests

# ==========================================
# 1. PROJECT SETTINGS
# ==========================================

START_DATE = "2026-10-20"
END_DATE = "2026-11-01"

LAT = 4.3667
LON = 100.9833

OUTPUT_DIR = "analysis_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

parameters = [
    "temperature",
    "humidity",
    "precipitation",
    "wind_speed"
]

start = pd.Timestamp(START_DATE, tz="UTC")
end = pd.Timestamp(END_DATE, tz="UTC") + pd.Timedelta(days=1)

# ==========================================
# 2. LOAD MEMBER A'S DATA
# ==========================================

obs = pd.read_csv("data/observations.csv")
fc = pd.read_csv("data/forecasts.csv")

obs["obs_time"] = pd.to_datetime(
    obs["obs_time"], utc=True
)

fc["target_time"] = pd.to_datetime(
    fc["target_time"], utc=True
)

fc["fetched_at"] = pd.to_datetime(
    fc["fetched_at"], utc=True
)

# Restrict forecasts to the project period
fc = fc[
    (fc["target_time"] >= start) &
    (fc["target_time"] < end)
].copy()

print("Original observations:", len(obs))
print("Forecast rows in project period:", len(fc))

# ==========================================
# 3. ROUND OBSERVATIONS TO NEAREST HOUR
# ==========================================

# Keep the original timestamp for traceability
obs["rounded_time"] = obs["obs_time"].dt.round("h")

obs["time_difference_minutes"] = (
    (obs["obs_time"] - obs["rounded_time"])
    .abs()
    .dt.total_seconds() / 60
)

# Allow observations within 30 minutes
obs = obs[
    (obs["rounded_time"] >= start) &
    (obs["rounded_time"] < end) &
    (obs["time_difference_minutes"] <= 30)
].copy()

# Keep the closest observation for each hour
obs = (
    obs.sort_values(
        ["time_difference_minutes", "obs_time"]
    )
    .drop_duplicates("rounded_time")
    .sort_values("rounded_time")
    .copy()
)

obs["source"] = "collected"

print("Unique rounded observation hours:", len(obs))

# ==========================================
# 4. DOWNLOAD HISTORICAL REFERENCE DATA
# ==========================================

archive_url = "https://archive-api.open-meteo.com/v1/archive"

archive_params = {
    "latitude": LAT,
    "longitude": LON,
    "start_date": START_DATE,
    "end_date": END_DATE,
    "hourly": (
        "temperature_2m,"
        "relative_humidity_2m,"
        "precipitation,"
        "wind_speed_10m"
    ),
    "timezone": "UTC"
}

archive = pd.DataFrame()

try:
    response = requests.get(
        archive_url,
        params=archive_params,
        timeout=60
    )
    response.raise_for_status()

    data = response.json()
    hourly = data["hourly"]

    archive = pd.DataFrame({
        "rounded_time": pd.to_datetime(
            hourly["time"], utc=True
        ),
        "temperature": hourly["temperature_2m"],
        "humidity": hourly["relative_humidity_2m"],
        "precipitation": hourly["precipitation"],
        "wind_speed": hourly["wind_speed_10m"]
    })

    archive["obs_time"] = archive["rounded_time"]
    archive["time_difference_minutes"] = 0.0
    archive["source"] = "archive"

    print("Archive rows retrieved:", len(archive))

except (requests.RequestException, KeyError, ValueError) as e:
    print("Archive data unavailable:", e)
    print("Continuing with collected observations only.")

# ==========================================
# 5. FILL MISSING HOURLY OBSERVATIONS
# ==========================================

collected_hours = set(obs["rounded_time"])

if not archive.empty:
    missing_archive = archive[
        ~archive["rounded_time"].isin(collected_hours)
    ].copy()

    reference = pd.concat(
        [obs, missing_archive],
        ignore_index=True
    )
else:
    reference = obs.copy()

reference = (
    reference.sort_values("rounded_time")
    .drop_duplicates("rounded_time")
    .reset_index(drop=True)
)

# Count missing hours after combining sources
expected_hours = pd.date_range(
    start=start,
    end=end - pd.Timedelta(hours=1),
    freq="h"
)

missing_hours = expected_hours.difference(
    reference["rounded_time"]
)

print("\nREFERENCE DATA SUMMARY")
print("Collected hours:", len(obs))
print("Total reference hours:", len(reference))
print("Still missing hours:", len(missing_hours))

reference.to_csv(
    f"{OUTPUT_DIR}/reference_weather.csv",
    index=False
)

pd.DataFrame({
    "missing_hour": missing_hours
}).to_csv(
    f"{OUTPUT_DIR}/missing_hours.csv",
    index=False
)

# ==========================================
# 6. MATCH FORECASTS WITH REFERENCE DATA
# ==========================================

matched = pd.merge(
    fc,
    reference,
    left_on="target_time",
    right_on="rounded_time",
    suffixes=("_forecast", "_actual")
)

# Exclude zero-hour forecasts
matched = matched[
    (matched["lead_hours"] >= 1) &
    (matched["fetched_at"] < matched["target_time"])
].copy()

# Preserve source and original observation time
matched = matched.sort_values(
    ["target_time", "lead_hours"]
)

print("\nMatched forecast rows:", len(matched))

# ==========================================
# 7. FUNCTION TO CALCULATE ACCURACY
# ==========================================

def calculate_metrics(data, parameter):

    forecast = pd.to_numeric(
        data[f"{parameter}_forecast"],
        errors="coerce"
    )

    actual = pd.to_numeric(
        data[f"{parameter}_actual"],
        errors="coerce"
    )

    valid = forecast.notna() & actual.notna()
    error = forecast[valid] - actual[valid]

    if len(error) == 0:
        return None

    return {
        "Parameter": parameter,
        "Samples": len(error),
        "MAE": np.abs(error).mean(),
        "RMSE": np.sqrt(np.mean(error ** 2)),
        "Bias": error.mean()
    }

# ==========================================
# 8. OVERALL FORECAST ACCURACY
# ==========================================

results = []

for param in parameters:
    result = calculate_metrics(matched, param)

    if result is not None:
        results.append(result)

summary = pd.DataFrame(
    results,
    columns=["Parameter", "Samples", "MAE", "RMSE", "Bias"]
)

print("\nOVERALL FORECAST ACCURACY")
print(summary.round(3).to_string(index=False))

# ==========================================
# 9. ACCURACY BY FORECAST HORIZON
# ==========================================

horizon_results = []

for lead in [1, 3, 6, 12, 24, 48]:

    subset = matched[
        matched["lead_hours"] == lead
    ]

    for param in parameters:
        result = calculate_metrics(subset, param)

        if result is not None:
            result["Lead Hours"] = lead
            horizon_results.append(result)

horizon_summary = pd.DataFrame(
    horizon_results,
    columns=[
        "Lead Hours", "Parameter", "Samples",
        "MAE", "RMSE", "Bias"
    ]
)

print("\nFORECAST ACCURACY BY HORIZON")
print(horizon_summary.round(3).to_string(index=False))

# ==========================================
# 10. ACCURACY BY REFERENCE SOURCE
# ==========================================

source_results = []

for source in ["collected", "archive"]:

    subset = matched[
        matched["source"] == source
    ]

    for param in parameters:
        result = calculate_metrics(subset, param)

        if result is not None:
            result["Source"] = source
            source_results.append(result)

source_summary = pd.DataFrame(
    source_results,
    columns=[
        "Source", "Parameter", "Samples",
        "MAE", "RMSE", "Bias"
    ]
)

print("\nACCURACY BY REFERENCE SOURCE")
print(source_summary.round(3).to_string(index=False))

# ==========================================
# 11. SAVE ANALYSIS RESULTS
# ==========================================

matched.to_csv(
    f"{OUTPUT_DIR}/matched_weather.csv",
    index=False
)

summary.to_csv(
    f"{OUTPUT_DIR}/accuracy_summary.csv",
    index=False
)

horizon_summary.to_csv(
    f"{OUTPUT_DIR}/horizon_accuracy.csv",
    index=False
)

source_summary.to_csv(
    f"{OUTPUT_DIR}/source_accuracy.csv",
    index=False
)

# ==========================================
# 12. TEMPERATURE COMPARISON GRAPH
# ==========================================

if not matched.empty:

    plot_data = (
        matched.sort_values(
            ["lead_hours", "target_time"]
        )
        .drop_duplicates("target_time")
        .sort_values("target_time")
    )

    plt.figure(figsize=(14, 6))

    plt.plot(
        plot_data["target_time"],
        plot_data["temperature_actual"],
        color="royalblue",
        linewidth=2,
        label="Reference Temperature"
    )

    plt.plot(
        plot_data["target_time"],
        plot_data["temperature_forecast"],
        color="darkorange",
        linewidth=1.8,
        linestyle="--",
        label="Forecast Temperature"
    )

    plt.xlabel("Time (UTC)")
    plt.ylabel("Temperature (°C)")

    plt.title(
        "Forecast vs Reference Temperature\n"
        "(Shortest Available Forecast Horizon)"
    )

    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=30)
    plt.tight_layout()

    plt.savefig(
        f"{OUTPUT_DIR}/temperature_comparison.png",
        dpi=300
    )

    plt.close()

print("\nAnalysis completed!")
print("Check the analysis_output folder.")
