"""Shared utilities for the AeroPulse file-based AutoML pipeline."""
from __future__ import annotations

import json
import logging
import os
import pickle
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    explained_variance_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

ML_ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = ML_ROOT / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
PROCESSED_DIR = DATASETS_DIR / "processed"
MODELS_DIR = ML_ROOT / "models"
METADATA_DIR = ML_ROOT / "metadata"
REPORTS_DIR = ML_ROOT / "reports"
TRAIN_CSV = PROCESSED_DIR / "train.csv"
METRICS_JSON = METADATA_DIR / "metrics.json"
BEST_MODEL = MODELS_DIR / "best_model.pkl"

POLLUTANT_COLUMNS = ["pm25", "pm10", "no2", "so2", "co", "o3"]
WEATHER_COLUMNS = ["temp", "humidity", "pressure", "wind", "rain", "clouds", "visibility"]
TARGET_COLUMN = "aqi"

ALIASES: Dict[str, List[str]] = {
    "date": ["date", "datetime", "timestamp", "time", "sampling_date"],
    "city": ["city", "location", "station", "area", "region"],
    "state": ["state", "province"],
    "country": ["country"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng"],
    "pm25": ["pm25", "pm2.5", "pm_2_5", "pm2_5"],
    "pm10": ["pm10", "pm_10"],
    "no2": ["no2", "nitrogen dioxide"],
    "so2": ["so2", "sulphur dioxide", "sulfur dioxide"],
    "co": ["co", "carbon monoxide"],
    "o3": ["o3", "ozone"],
    "temp": ["temp", "temperature", "temperature_2m"],
    "humidity": ["humidity", "relative_humidity", "rh"],
    "pressure": ["pressure", "surface_pressure"],
    "wind": ["wind", "wind_speed", "windspeed", "wind_speed_10m"],
    "rain": ["rain", "rainfall", "precipitation"],
    "clouds": ["clouds", "cloud_cover", "cloudcover"],
    "visibility": ["visibility"],
    "aqi": ["aqi", "air quality index", "aqi_value"],
}


def configure_logging() -> logging.Logger:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(REPORTS_DIR / "automl.log", encoding="utf-8"),
        ],
    )
    return logging.getLogger("aeropulse.automl")


def ensure_dirs() -> None:
    for path in (RAW_DIR, PROCESSED_DIR, MODELS_DIR, METADATA_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ML_ROOT.parents[1],
            text=True,
        ).strip()
    except Exception:
        return None


def detect_columns(columns: Iterable[str]) -> Dict[str, str]:
    normalized = {str(col).lower().strip().replace("-", "_"): str(col) for col in columns}
    mapping: Dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            key = alias.lower().strip().replace("-", "_")
            if key in normalized:
                mapping[canonical] = normalized[key]
                break
        if canonical not in mapping:
            for lower, original in normalized.items():
                if any(len(alias) >= 3 and alias.lower().replace("-", "_") in lower for alias in aliases):
                    mapping[canonical] = original
                    break
    return mapping


def normalize_schema(frame: pd.DataFrame) -> pd.DataFrame:
    mapping = detect_columns(frame.columns)
    renamed = {source: target for target, source in mapping.items()}
    frame = frame.rename(columns=renamed).copy()
    for column in ["date", "city", "state", "country", "latitude", "longitude", *POLLUTANT_COLUMNS, *WEATHER_COLUMNS, TARGET_COLUMN]:
        if column not in frame:
            frame[column] = np.nan
    return frame


def read_raw_csvs() -> Tuple[pd.DataFrame, List[str]]:
    ensure_dirs()
    files = sorted(RAW_DIR.glob("*.csv"))
    frames = []
    for path in files:
        frame = pd.read_csv(path)
        frame["dataset_name"] = path.stem
        frames.append(normalize_schema(frame))
    if not frames:
        return pd.DataFrame(), []
    return pd.concat(frames, ignore_index=True), [path.name for path in files]


def mape(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    true = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    mask = true != 0
    return float(np.mean(np.abs((true[mask] - pred[mask]) / true[mask])) * 100) if mask.any() else 0.0


def regression_metrics(y_true: Iterable[float], y_pred: Iterable[float]) -> Dict[str, float]:
    return {
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "mse": round(float(mean_squared_error(y_true, y_pred)), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "mape": round(mape(y_true, y_pred), 4),
        "explained_variance": round(float(explained_variance_score(y_true, y_pred)), 4),
    }


def model_size_mb(path: Path) -> float:
    return round(path.stat().st_size / (1024 * 1024), 4) if path.exists() else 0.0


def save_pickle(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as file:
        pickle.dump(payload, file)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def timer() -> Tuple[float, Any]:
    started = time.perf_counter()
    return started, lambda: round(time.perf_counter() - started, 4)


def version_id() -> str:
    return datetime.now(timezone.utc).strftime("v%Y%m%d%H%M%S")
