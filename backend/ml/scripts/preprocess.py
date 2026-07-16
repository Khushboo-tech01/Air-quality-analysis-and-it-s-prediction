"""Preprocess raw AQI datasets into a validated canonical table."""
from __future__ import annotations

import numpy as np
import pandas as pd

from utils import POLLUTANT_COLUMNS, PROCESSED_DIR, TARGET_COLUMN, WEATHER_COLUMNS, configure_logging, ensure_dirs, read_raw_csvs

RANGES = {
    "pm25": (0, 1000), "pm10": (0, 1500), "no2": (0, 1000), "so2": (0, 1000),
    "co": (0, 100), "o3": (0, 1000), "temp": (-80, 70), "humidity": (0, 100),
    "pressure": (800, 1100), "wind": (0, 80), "rain": (0, 500), "clouds": (0, 100),
    "visibility": (0, 100000), TARGET_COLUMN: (0, 500),
}


def _clean_numeric(frame: pd.DataFrame, column: str) -> None:
    frame[column] = pd.to_numeric(frame[column], errors="coerce")
    low, high = RANGES[column]
    frame.loc[~frame[column].between(low, high), column] = np.nan


def preprocess() -> pd.DataFrame:
    logger = configure_logging()
    ensure_dirs()
    frame, raw_files = read_raw_csvs()
    if frame.empty:
        raise RuntimeError("No raw CSV datasets found. Run download_dataset.py first.")

    frame["date"] = pd.to_datetime(frame["date"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["date"]).drop_duplicates()
    for column in [*POLLUTANT_COLUMNS, *WEATHER_COLUMNS, TARGET_COLUMN]:
        _clean_numeric(frame, column)

    frame = frame.sort_values(["city", "date"])
    numeric = [*POLLUTANT_COLUMNS, *WEATHER_COLUMNS]
    frame[numeric] = frame.groupby("city", dropna=False)[numeric].transform(lambda s: s.ffill().bfill().fillna(s.median()))
    frame = frame.dropna(subset=["pm25", "pm10", "temp", "humidity", "pressure", "wind", TARGET_COLUMN])

    for column in [*POLLUTANT_COLUMNS, *WEATHER_COLUMNS, TARGET_COLUMN]:
        q1 = frame[column].quantile(0.01)
        q99 = frame[column].quantile(0.99)
        frame = frame[frame[column].between(q1, q99)]

    frame["date"] = frame["date"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    frame["source_files"] = ", ".join(raw_files)
    output = PROCESSED_DIR / "preprocessed.csv"
    frame.to_csv(output, index=False)
    logger.info("Preprocessed dataset saved: %s rows at %s", len(frame), output)
    return frame


if __name__ == "__main__":
    preprocess()
