"""Advanced feature engineering for AQI AutoML."""
from __future__ import annotations

import numpy as np
import pandas as pd

from utils import POLLUTANT_COLUMNS, PROCESSED_DIR, TARGET_COLUMN, TRAIN_CSV, configure_logging


def _season(month: int) -> int:
    if month in (12, 1, 2):
        return 1
    if month in (3, 4, 5):
        return 2
    if month in (6, 7, 8, 9):
        return 3
    return 4


def engineer_features(input_path=PROCESSED_DIR / "preprocessed.csv") -> pd.DataFrame:
    logger = configure_logging()
    frame = pd.read_csv(input_path)
    frame["date_dt"] = pd.to_datetime(frame["date"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["date_dt"]).sort_values(["city", "date_dt"])
    frame["month"] = frame["date_dt"].dt.month
    frame["weekday"] = frame["date_dt"].dt.weekday
    frame["weekend"] = frame["weekday"].isin([5, 6]).astype(int)
    frame["day_of_year"] = frame["date_dt"].dt.dayofyear
    frame["hour"] = frame["date_dt"].dt.hour
    frame["season"] = frame["month"].map(_season)
    frame["rush_hour_indicator"] = frame["hour"].isin([8, 9, 18, 19, 20]).astype(int)
    frame["festival_indicator"] = frame["date_dt"].dt.strftime("%m-%d").isin(["01-01", "08-15", "10-02", "11-01", "12-25"]).astype(int)
    frame["rain_indicator"] = (frame["rain"] > 0).astype(int)
    frame["wind_category"] = pd.cut(frame["wind"], bins=[-0.1, 2, 5, 10, 100], labels=[0, 1, 2, 3]).astype(float)

    for column in ["temp", "humidity", "pressure", "wind"]:
        frame[f"{column}_trend"] = frame.groupby("city")[column].diff().fillna(0)
    for column in [*POLLUTANT_COLUMNS, TARGET_COLUMN]:
        frame[f"{column}_lag_1"] = frame.groupby("city")[column].shift(1)
        frame[f"{column}_lag_24"] = frame.groupby("city")[column].shift(24)
        frame[f"{column}_rolling_24h"] = frame.groupby("city")[column].transform(lambda s: s.rolling(24, min_periods=1).mean())
        frame[f"{column}_rolling_7d"] = frame.groupby("city")[column].transform(lambda s: s.rolling(24 * 7, min_periods=1).mean())

    frame["pm25_pm10_ratio"] = frame["pm25"] / frame["pm10"].clip(lower=1e-6)
    frame["no2_o3_ratio"] = frame["no2"] / frame["o3"].clip(lower=1e-6)
    frame["pm25_humidity_interaction"] = frame["pm25"] * frame["humidity"] / 100
    frame["pm10_wind_interaction"] = frame["pm10"] / (frame["wind"] + 1)
    frame["o3_temp_interaction"] = frame["o3"] * frame["temp"]
    frame["traffic_estimate"] = frame["rush_hour_indicator"] * (frame["pm25"] + frame["no2"])
    frame["industrial_indicator"] = ((frame["so2"] > frame["so2"].median()) & (frame["pm10"] > frame["pm10"].median())).astype(int)
    frame["population_density"] = frame.groupby("city")["city"].transform("count")

    frame = frame.replace([np.inf, -np.inf], np.nan)
    numeric = frame.select_dtypes(include=[np.number]).columns
    frame[numeric] = frame[numeric].fillna(frame[numeric].median(numeric_only=True)).fillna(0)
    frame = frame.drop(columns=["date_dt"])
    TRAIN_CSV.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(TRAIN_CSV, index=False)
    logger.info("Feature engineered training dataset saved: %s rows, %s columns at %s", len(frame), len(frame.columns), TRAIN_CSV)
    return frame


if __name__ == "__main__":
    engineer_features()
