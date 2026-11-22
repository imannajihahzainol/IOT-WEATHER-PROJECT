
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Get current folder
BASE_DIR = Path(__file__).resolve().parent

# Read CSV file
csv_path = BASE_DIR / "horizon_accuracy.csv"
df = pd.read_csv(csv_path)

# Remove extra spaces from column names
df.columns = df.columns.str.strip()

# Prepare graph
plt.figure(figsize=(10, 6))

# Weather parameters
parameters = [
    "temperature",
    "humidity",
    "precipitation",
    "wind_speed"
]

# Generate a line for each parameter
for parameter in parameters:

    data = df[df["Parameter"] == parameter].copy()

    data = data.sort_values("Lead Hours")

    plt.plot(
        data["Lead Hours"],
        data["MAE"],
        marker="o",
        linewidth=2,
        label=parameter.replace("_", " ").title()
    )

# Graph formatting
plt.title("Weather Forecast Accuracy by Lead Time")
plt.xlabel("Forecast Lead Time (Hours)")
plt.ylabel("Mean Absolute Error (MAE)")

plt.xticks(sorted(df["Lead Hours"].unique()))
plt.grid(True, alpha=0.3)
plt.legend(title="Weather Parameters")
plt.tight_layout()

# Save graph
output_path = BASE_DIR / "all_parameters_accuracy.png"

plt.savefig(output_path, dpi=300)
plt.show()

print(f"Graph successfully saved at: {output_path}")
