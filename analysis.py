
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# 1. Load the collected data
obs = pd.read_csv("data/observations.csv")
fc = pd.read_csv("data/forecasts.csv")

# 2. Convert timestamps to UTC
obs["obs_time"] = pd.to_datetime(obs["obs_time"], utc=True)
fc["target_time"] = pd.to_datetime(fc["target_time"], utc=True)
fc["fetched_at"] = pd.to_datetime(fc["fetched_at"], utc=True)

# 3. Keep exact-hour observations
obs = obs[
    (obs["obs_time"].dt.minute == 0) &
    (obs["obs_time"].dt.second == 0)
].copy()

# 4. Match observations with forecasts
matched = pd.merge(
    fc,
    obs,
    left_on="target_time",
    right_on="obs_time",
    suffixes=("_forecast", "_actual")
)

# Keep forecasts recorded before the target hour
matched = matched[
    (matched["lead_hours"] >= 1) &
    (matched["fetched_at"] < matched["target_time"])
].copy()

parameters = [
    "temperature",
    "humidity",
    "precipitation",
    "wind_speed"
]

# 5. Function to calculate accuracy
def calculate_metrics(data, parameter):
    forecast = data[f"{parameter}_forecast"]
    actual = data[f"{parameter}_actual"]

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

# 6. Overall accuracy
results = []

for param in parameters:
    result = calculate_metrics(matched, param)
    if result is not None:
        results.append(result)

summary = pd.DataFrame(results)

print("\nOVERALL FORECAST ACCURACY")
print("Matched forecast rows:", len(matched))
print(summary.round(3).to_string(index=False))

# 7. Accuracy by forecast horizon
horizon_results = []

for lead in [1, 3, 6, 12, 24, 48]:
    subset = matched[matched["lead_hours"] == lead]

    for param in parameters:
        result = calculate_metrics(subset, param)

        if result is not None:
            result["Lead Hours"] = lead
            horizon_results.append(result)

horizon_summary = pd.DataFrame(horizon_results)

print("\nFORECAST ACCURACY BY HORIZON")
if not horizon_summary.empty:
    print(horizon_summary.round(3).to_string(index=False))
else:
    print("No matching horizon records.")

# 8. Save outputs
os.makedirs("analysis_output", exist_ok=True)

matched.to_csv(
    "analysis_output/matched_weather.csv",
    index=False
)
summary.to_csv(
    "analysis_output/accuracy_summary.csv",
    index=False
)
horizon_summary.to_csv(
    "analysis_output/horizon_accuracy.csv",
    index=False
)

# 9. Plot temperature forecast vs actual
if not matched.empty:
    # Use one forecast per observation for clarity
    plot_data = (
        matched.sort_values("lead_hours")
        .drop_duplicates("target_time")
        .sort_values("target_time")
    )

    plt.figure(figsize=(11, 5))

    plt.plot(
        plot_data["target_time"],
        plot_data["temperature_actual"],
        marker="o",
        label="Reference Temperature"
    )

    plt.plot(
        plot_data["target_time"],
        plot_data["temperature_forecast"],
        marker="x",
        label="Forecast Temperature"
    )

    plt.xlabel("Time (UTC)")
    plt.ylabel("Temperature (°C)")
    plt.title("Forecast vs Reference Temperature")
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=30)
    plt.tight_layout()

    plt.savefig(
        "analysis_output/temperature_comparison.png",
        dpi=200
    )
    plt.close()

print("\nAnalysis completed!")
print("Files saved in analysis_output folder.")
