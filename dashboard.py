import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="Seri Iskandar Weather Dashboard", 
    layout="wide"
)
 #CSS Style
 # Mode is based on the system settings, not the Streamlit theme.
st.markdown("""
<style>
    /* Light Mode */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #FFF4E6 !important;  
        color: #2D2438 !important;         
    }
    h1, h2, h3, h4, p, span {
        color: #2D2438 !important;
    }
    div[data-testid="stMetricLabel"] * {
        color: #554863 !important;           
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important; 
        border: 1.5px solid #9CAF88 !important; 
        border-radius: 16px !important;
        padding: 16px 20px !important;
    }
    .chart-card {
        background-color: #FFFFFF !important;  
        border: 1.5px solid #9CAF88 !important; 
        border-radius: 20px !important;
        padding: 20px !important;
        margin-bottom: 24px !important;
    }

    /* Dark Mode */
    @media (prefers-color-scheme: dark) {
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #2F2736 !important; 
            color: #E8E5EC !important;          
        }
        h1, h2, h3, h4, p, span {
            color: #E8E5EC !important;
        }
        div[data-testid="stMetricLabel"] * {
            color: #C0B5CC !important;          
        }
        div[data-testid="stMetric"] {
            background-color: #3C3146 !important;
            border: 1.5px solid #9CAF88 !important;
        }
        .chart-card {
            background-color: #382D42 !important;
            border: 1.5px solid #9CAF88 !important;
        }
    }
    div[data-testid="stMetricValue"] * {
        color: #9CAF88 !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("Seri Iskandar Weather & Forecast Verification Dashboard")
st.caption("IoT Weather Monitoring (Seri Iskandar)")

# 1. File Finder Helper
def find_file(filename):
    if os.path.exists(filename):
        return filename
    subpath = os.path.join("analysis_output", filename)
    if os.path.exists(subpath):
        return subpath
    return filename

try:
    df_matched = pd.read_csv(find_file("matched_weather.csv"))
    df_horizon = pd.read_csv(find_file("horizon_accuracy.csv"))
except Exception as e:
    st.error(f"Error loading CSV files: {e}")
    st.stop()

def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

col_time = find_col(df_matched, ["target_time", "timestamp", "time", "date"])
col_temp_act = find_col(df_matched, ["temp_actual", "actual_temperature", "temperature_actual", "temp_obs", "temperature"])
col_temp_fc = find_col(df_matched, ["temp_forecast", "forecast_temperature", "temperature_forecast", "forecast_temp"])
col_rain_act = find_col(df_matched, ["precipitation_actual", "precipitation", "rain_actual", "actual_rain", "rainfall_actual", "rainfall", "rain_obs", "rain"])
col_rain_fc = find_col(df_matched, ["precipitation_forecast", "precipitation", "rain_forecast", "forecast_rain", "rainfall_forecast"])
col_hum_act = find_col(df_matched, ["humidity_actual", "actual_humidity", "humidity", "humidity_obs"])
col_wind_act = find_col(df_matched, ["wind_actual", "actual_wind_speed", "wind_speed", "wind_speed_actual"])
col_lead = find_col(df_matched, ["lead_hours", "horizon", "horizon_hours", "lead_time"])

if col_time:
    df_matched[col_time] = pd.to_datetime(df_matched[col_time])

# 2. Sidebar Filters
st.sidebar.header("Filter Settings")
if col_lead:
    lead_times = sorted(df_matched[col_lead].dropna().unique())
    selected_lead = st.sidebar.selectbox("Select Forecast Horizon (Lead Hours)", lead_times, index=0)
    view_df = df_matched[df_matched[col_lead] == selected_lead].sort_values(col_time if col_time else df_matched.columns[0])
else:
    selected_lead = "All"
    view_df = df_matched.copy()

# 3. KPI Metric Cards
latest = view_df.iloc[-1]
col1, col2, col3, col4 = st.columns(4)

temp_val = latest.get(col_temp_act, None)
col1.metric("Observed Temp", f"{float(temp_val):.1f} °C" if pd.notnull(temp_val) else "N/A")

rain_val = latest.get(col_rain_act, None)
col2.metric("Observed Rainfall", f"{float(rain_val):.1f} mm" if pd.notnull(rain_val) else "0.0 mm")

hum_val = latest.get(col_hum_act, None)
col3.metric("Observed Humidity", f"{float(hum_val):.0f}%" if pd.notnull(hum_val) else "N/A")

wind_val = latest.get(col_wind_act, None)
col4.metric("Observed Wind", f"{float(wind_val):.1f} km/h" if pd.notnull(wind_val) else "N/A")

st.divider()

# 4. Temperature Comparison Chart
st.subheader(f"Temperature Comparison: Observed vs. Forecast")
if col_time and col_temp_act and col_temp_fc:
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Scatter(
        x=view_df[col_time], y=view_df[col_temp_act],
        mode="lines", name="Actual Observed",
        line=dict(color="#ef9826", width=2)
    ))
    fig_temp.add_trace(go.Scatter(
        x=view_df[col_time], y=view_df[col_temp_fc],
        mode="lines", name=f"Forecast",
        line=dict(color="#acb0a4", dash="dash")
    ))
    fig_temp.update_layout(
        xaxis_title="Time", 
        yaxis_title="Temperature (°C)",
        hovermode="x unified", 
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_temp, use_container_width=True)
else:
    st.info("Temperature comparison columns could not be found.")

# 5. Accuracy Breakdown (Horizon Error)
st.divider()
st.subheader("Model Error Metrics by Forecast Horizon")
c_table, c_chart = st.columns([1, 1])

with c_table:
    st.write("Horizon Accuracy Breakdown Table:")
    st.dataframe(df_horizon, use_container_width=True, hide_index=True)

with c_chart:
    h_x = find_col(df_horizon, ["horizon_hours", "lead_hours", "horizon"]) or df_horizon.columns[0]
    error_cols = [c for c in ["temp_mae", "temp_rmse", "MAE", "RMSE", "mae", "rmse"] if c in df_horizon.columns]
    
    if error_cols:
        fig_err = px.bar(
            df_horizon, x=h_x, y=error_cols, barmode="group",
            title="Temperature Error (MAE vs RMSE)",
            labels={"value": "Error (°C)", "variable": "Metric"}
        )
        fig_err.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Forecast Horizon (Hours)",
            yaxis_title="Error (°C)",
            legend_title="Error Metric"
        )
        st.plotly_chart(fig_err, use_container_width=True)

        # Run using Terminal : python -m streamlit run dashboard.py 