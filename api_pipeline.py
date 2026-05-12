import requests
import pandas as pd
from sqlalchemy import create_engine
import joblib
from datetime import datetime

# MySQL connection settings
MYSQL_USER = "analyst"
MYSQL_PASSWORD = "analysis123"
MYSQL_HOST = "localhost"
MYSQL_PORT = "3307"
MYSQL_DATABASE = "weather_traffic_db"

# pull weather data
weather_url = "https://archive-api.open-meteo.com/v1/archive"

weather_params = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "hourly": [
        "temperature_2m",
        "rain",
        "snowfall",
        "weather_code"
    ],
    "timezone": "America/New_York"
}

weather_response = requests.get(weather_url, params=weather_params)
weather_data = weather_response.json()

weather_df = pd.DataFrame(weather_data["hourly"])
weather_df["time"] = pd.to_datetime(weather_df["time"])
weather_df["date"] = pd.to_datetime(weather_df["time"].dt.date)
weather_df["hour"] = weather_df["time"].dt.hour

print("WEATHER DATA")
print(weather_df.head())


# pull traffic data
traffic_url = "https://data.cityofnewyork.us/resource/7ym2-wayt.json"

all_traffic = []
offset = 0
limit = 50000

while True:
    traffic_params = {
        "$limit": limit,
        "$offset": offset,
        "$where": "yr = 2024"
    }

    traffic_response = requests.get(traffic_url, params=traffic_params)
    traffic_data = traffic_response.json()

    if not traffic_data:
        break

    all_traffic.extend(traffic_data)
    offset += limit

    print(f"Fetched {len(all_traffic)} traffic rows so far...")

traffic_df = pd.DataFrame(all_traffic)

print("\nTOTAL RAW TRAFFIC ROWS:", len(traffic_df))


# clean and rename columns
traffic_df["date"] = pd.to_datetime({
    "year": traffic_df["yr"].astype(int),
    "month": traffic_df["m"].astype(int),
    "day": traffic_df["d"].astype(int)
})

traffic_df["hour"] = traffic_df["hh"].astype(int)
traffic_df["vol"] = traffic_df["vol"].astype(float)

traffic_df = traffic_df.rename(columns={
    "boro": "borough",
    "vol": "vehicle_volume"
})

traffic_df = traffic_df[
    [
        "date",
        "hour",
        "borough",
        "street",
        "direction",
        "vehicle_volume"
    ]
]

print("\nCLEANED TRAFFIC DATA")
print(traffic_df.head())


# group by street and hour
traffic_agg = (
    traffic_df
    .groupby(
        [
            "date",
            "hour",
            "borough",
            "street",
            "direction"
        ]
    )["vehicle_volume"]
    .mean()
    .reset_index()
    .rename(columns={"vehicle_volume": "avg_vehicle_volume"})
)

print("\nAGGREGATED TRAFFIC DATA")
print(traffic_agg.head())


# join weather and traffic
merged_df = pd.merge(
    weather_df,
    traffic_agg,
    on=["date", "hour"],
    how="inner"
)

print("\nMERGED DATA")
print(merged_df.head())


# normalize volume into index
merged_df["normal_volume"] = (
    merged_df
    .groupby(["borough", "street", "direction", "hour"])["avg_vehicle_volume"]
    .transform("mean")
)

merged_df["traffic_index"] = (
    merged_df["avg_vehicle_volume"] / merged_df["normal_volume"]
)

# drop bad rows
merged_df = merged_df[
    (merged_df["normal_volume"] > 0) &
    (merged_df["traffic_index"].notna())
]


# cap extreme outliers
p99 = merged_df["traffic_index"].quantile(0.99)
merged_df["traffic_index_capped"] = merged_df["traffic_index"].clip(upper=p99)

print(f"\nCapped traffic_index at 99th percentile: {p99:.2f}")


# quick checks
total_possible_borough = 365 * 24 * 5
coverage_pct = (len(merged_df) / total_possible_borough) * 100

print(f"\nBOROUGH-LEVEL COVERAGE COMPARISON: {len(merged_df)}/{total_possible_borough} rows ({coverage_pct:.1f}%)")
print("\nSHAPE:", merged_df.shape)
print("\nNULLS:\n", merged_df.isnull().sum())
print("\nDATE RANGE:", merged_df["date"].min(), "to", merged_df["date"].max())
print("\nBOROUGHS:", merged_df["borough"].unique())
print("\nCAPPED TRAFFIC INDEX SUMMARY:\n", merged_df["traffic_index_capped"].describe())


# load into MySQL
engine = create_engine(
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
)

merged_df.to_sql(
    "weather_traffic_data",
    con=engine,
    if_exists="replace",
    index=False
)

print(f"\nWrote {len(merged_df)} rows to MySQL table 'weather_traffic_data'")


# live prediction for current hour

# get current hour weather from forecast API
now = datetime.now()
current_hour = now.hour

forecast_url = "https://api.open-meteo.com/v1/forecast"
forecast_params = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "hourly": ["temperature_2m", "rain", "snowfall"],
    "timezone": "America/New_York",
    "forecast_days": 1
}
forecast = requests.get(forecast_url, params=forecast_params).json()

current_temp  = forecast["hourly"]["temperature_2m"][current_hour]
current_rain  = forecast["hourly"]["rain"][current_hour]
current_snow  = forecast["hourly"]["snowfall"][current_hour]

# get previous hour avg volume from MySQL
prev_hour = current_hour - 1 if current_hour > 0 else 23
prev_vol_query = f"""
    SELECT AVG(avg_vehicle_volume) as prev_volume
    FROM weather_traffic_data
    WHERE hour = {prev_hour}
"""
prev_volume = pd.read_sql(prev_vol_query, con=engine)["prev_volume"].values[0]

# flags
rush_hour  = 1 if (7 <= current_hour <= 9) or (16 <= current_hour <= 19) else 0
is_weekend = 1 if datetime.now().weekday() >= 5 else 0

# load saved model
model_b = joblib.load("model_b.pkl")

# predict
features = pd.DataFrame([{
    "rain":                  current_rain,
    "temperature":           current_temp,
    "snowfall":              current_snow,
    "previous_hour_traffic": prev_volume,
    "rush_hour":             rush_hour,
    "is_weekend":            is_weekend
}])

predicted_volume = model_b.predict(features)[0]
predicted_volume = max(0, predicted_volume)

# congestion label
def congestion_label(vol):
    if vol < 50:   return "Low"
    elif vol < 150: return "Moderate"
    elif vol < 300: return "High"
    else:           return "Severe"

congestion = congestion_label(predicted_volume)

# write to MySQL
live_pred = pd.DataFrame([{
    "timestamp":            now.strftime("%Y-%m-%d %H:%M:%S"),
    "hour":                 current_hour,
    "temperature":          current_temp,
    "rain":                 current_rain,
    "snowfall":             current_snow,
    "rush_hour":            rush_hour,
    "is_weekend":           is_weekend,
    "prev_hour_volume":     round(prev_volume, 1),
    "predicted_volume":     round(predicted_volume, 1),
    "congestion_level":     congestion
}])

live_pred.to_sql(
    "live_prediction",
    con=engine,
    if_exists="replace",
    index=False
)

print(f"\nLIVE PREDICTION — {now.strftime('%Y-%m-%d %H:%M')}")
print(f"  Temp: {current_temp}°C  Rain: {current_rain}mm  Snow: {current_snow}mm")
print(f"  Rush hour: {'Yes' if rush_hour else 'No'}")
print(f"  Prev hour volume: {prev_volume:.0f} vehicles")
print(f"  Predicted volume: {predicted_volume:.0f} vehicles/hour")
print(f"  Congestion level: {congestion}")