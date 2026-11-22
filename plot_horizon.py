
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Get project folder
BASE_DIR = Path(__file__).resolve().parent

# Read horizon accuracy data
csv_path = BASE_DIR / "horizon_accuracy.csv"
df = pd.read_csv(csv_path)

# Select temperature data
temperature = df[df["Parameter"] == "temperature"].copy()

# Sort by forecast lead time
temperature = temperature.sort_values("Lead Hours")

# Generate line graph
plt.figure(figsize=(9, 5))

plt.plot(
    temperature["Lead Hours"],
    temperature["MAE"],
    marker="o",
    linewidth=2,
    label="Temperature MAE"
)

plt.title("Temperature Forecast Accuracy by Lead Time")
plt.xlabel("Forecast Lead Time (Hours)")
plt.ylabel("Mean Absolute Error (MAE)")
plt.xticks(temperature["Lead Hours"])
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()

# Save graph
output_path = BASE_DIR / "horizon_accuracy_graph.png"
plt.savefig(output_path, dpi=300)

plt.show()

print(f"Graph successfully saved at: {output_path}")
