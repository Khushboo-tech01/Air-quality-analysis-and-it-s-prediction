"""Automated AQI model training, evaluation, and versioning."""
from __future__ import annotations

import asyncio
import logging
import os
import pickle
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

try:  # Optional but available in the current requirements.
    from xgboost import XGBRegressor
except Exception:  # pragma: no cover - optional dependency import guard
    XGBRegressor = None

from services.data_collector import FEATURE_COLUMNS

logger = logging.getLogger("aeropulse.training")

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
BEST_MODEL_PATH = MODELS_DIR / "best_model.pkl"
FINAL_MODEL_PATH = MODELS_DIR / "final_model.pkl"


def _git_commit() -> Optional[str]:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).resolve().parents[2], text=True).strip()
    except Exception:
        return None


def _mape(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def _metrics(y_true, y_pred) -> Dict[str, float]:
    return {
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "mape": round(_mape(y_true, y_pred), 4),
    }


def _model_candidates(random_state: int = 42) -> Dict[str, Tuple[Pipeline, Dict[str, List[Any]]]]:
    candidates: Dict[str, Tuple[Pipeline, Dict[str, List[Any]]]] = {
        "Linear Regression": (
            Pipeline([("scaler", RobustScaler()), ("model", LinearRegression())]),
            {},
        ),
        "Random Forest": (
            Pipeline([("scaler", RobustScaler()), ("model", RandomForestRegressor(random_state=random_state, n_jobs=-1))]),
            {"model__n_estimators": [120, 220], "model__max_depth": [8, 14, None], "model__min_samples_leaf": [1, 3]},
        ),
        "Gradient Boosting": (
            Pipeline([("scaler", RobustScaler()), ("model", GradientBoostingRegressor(random_state=random_state))]),
            {"model__n_estimators": [120, 220], "model__learning_rate": [0.04, 0.08], "model__max_depth": [2, 3]},
        ),
    }
    if XGBRegressor is not None:
        candidates["XGBoost"] = (
            Pipeline([("scaler", RobustScaler()), ("model", XGBRegressor(random_state=random_state, objective="reg:squarederror", n_jobs=2))]),
            {"model__n_estimators": [140, 240], "model__max_depth": [3, 5], "model__learning_rate": [0.04, 0.08]},
        )
    return candidates


async def _load_training_frame(db) -> pd.DataFrame:
    rows = []
    cursor = db.training_dataset.find({}, {"_id": 0})
    async for row in cursor:
        rows.append(row)
    return pd.DataFrame(rows)


def _prepare_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    for column in FEATURE_COLUMNS + ["aqi"]:
        if column not in frame:
            frame[column] = 0.0
    frame = frame.replace([np.inf, -np.inf], np.nan)
    for column in FEATURE_COLUMNS + ["aqi"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame[FEATURE_COLUMNS] = frame[FEATURE_COLUMNS].fillna(frame[FEATURE_COLUMNS].median(numeric_only=True)).fillna(0)
    frame = frame.dropna(subset=["aqi"])
    q_low, q_high = frame["aqi"].quantile([0.01, 0.99])
    frame = frame[(frame["aqi"] >= q_low) & (frame["aqi"] <= q_high)]
    return frame


def _feature_importance(best_pipeline: Pipeline, feature_keys: List[str]) -> List[Dict[str, float]]:
    model = best_pipeline.named_steps.get("model")
    values = getattr(model, "feature_importances_", None)
    if values is None and hasattr(model, "coef_"):
        values = np.abs(np.asarray(model.coef_))
    if values is None:
        return []
    total = float(np.sum(np.abs(values))) or 1.0
    rows = [
        {"feature": feature, "importance": round(float(abs(value) / total), 5)}
        for feature, value in zip(feature_keys, values)
    ]
    return sorted(rows, key=lambda item: item["importance"], reverse=True)


def _train_sync(frame: pd.DataFrame) -> Dict[str, Any]:
    started = time.time()
    frame = _prepare_frame(frame)
    if len(frame) < 100:
        raise ValueError("At least 100 training rows are required. Run data collection first.")

    X = frame[FEATURE_COLUMNS]
    y = frame["aqi"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    cv = KFold(n_splits=5, shuffle=True, random_state=42)

    results = []
    best: Optional[Dict[str, Any]] = None
    for name, (pipeline, grid) in _model_candidates().items():
        logger.info("Training candidate model: %s", name)
        search = GridSearchCV(
            estimator=pipeline,
            param_grid=grid or {},
            scoring="neg_root_mean_squared_error",
            cv=cv,
            n_jobs=1,
        )
        model_started = time.time()
        search.fit(X_train, y_train)
        predictions = search.best_estimator_.predict(X_test)
        metrics = _metrics(y_test, predictions)
        row = {
            "algorithm": name,
            "metrics": metrics,
            "cv_rmse": round(float(-search.best_score_), 4),
            "best_params": search.best_params_,
            "training_time_seconds": round(time.time() - model_started, 2),
            "estimator": search.best_estimator_,
        }
        results.append({k: v for k, v in row.items() if k != "estimator"})
        if best is None or metrics["rmse"] < best["metrics"]["rmse"]:
            best = row

    assert best is not None
    estimator: Pipeline = best["estimator"]
    predictions = estimator.predict(X_test)
    residuals = np.asarray(y_test) - np.asarray(predictions)
    version = datetime.now(timezone.utc).strftime("aqi-%Y%m%d-%H%M%S")
    means = X.mean(numeric_only=True).to_dict()
    stds = X.std(numeric_only=True).replace(0, 1).fillna(1).to_dict()
    artifact = {
        "model": estimator,
        "best_name": best["algorithm"],
        "best_metrics": best["metrics"],
        "all_results": results,
        "feature_keys": FEATURE_COLUMNS,
        "feature_importance": _feature_importance(estimator, FEATURE_COLUMNS),
        "means": means,
        "stds": stds,
        "residual_std": float(np.std(residuals)) if len(residuals) else None,
        "dataset_rows": int(len(frame)),
        "model_version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
    }
    return {
        "artifact": artifact,
        "results": results,
        "best": {k: v for k, v in best.items() if k != "estimator"},
        "duration_seconds": round(time.time() - started, 2),
    }


async def current_production_metrics(db) -> Optional[Dict[str, Any]]:
    return await db.model_metrics.find_one(sort=[("training_date", -1)])


async def train_production_model(db, replace_only_if_better: bool = True) -> Dict[str, Any]:
    """Train all candidate models and promote only if quality improves."""
    started_at = datetime.now(timezone.utc).isoformat()
    await db.training_logs.insert_one({"type": "training", "status": "started", "created_at": started_at})
    frame = await _load_training_frame(db)
    result = await asyncio.to_thread(_train_sync, frame)
    artifact = result["artifact"]
    previous = await current_production_metrics(db)
    previous_rmse = (previous or {}).get("rmse")
    new_rmse = artifact["best_metrics"]["rmse"]
    promoted = previous_rmse is None or not replace_only_if_better or new_rmse <= float(previous_rmse)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    version_path = MODELS_DIR / f"{artifact['model_version']}.pkl"
    with open(version_path, "wb") as file:
        pickle.dump(artifact, file)
    if promoted:
        with open(BEST_MODEL_PATH, "wb") as file:
            pickle.dump(artifact, file)
        with open(FINAL_MODEL_PATH, "wb") as file:
            pickle.dump(artifact, file)

    metrics_doc = {
        "algorithm": artifact["best_name"],
        "rmse": artifact["best_metrics"]["rmse"],
        "mae": artifact["best_metrics"]["mae"],
        "r2": artifact["best_metrics"]["r2"],
        "mape": artifact["best_metrics"]["mape"],
        "dataset_size": artifact["dataset_rows"],
        "model_version": artifact["model_version"],
        "training_date": artifact["trained_at"],
        "training_time_seconds": result["duration_seconds"],
        "git_commit": artifact["git_commit"],
        "promoted": promoted,
        "model_path": str(version_path),
        "feature_importance": artifact["feature_importance"],
        "candidate_results": result["results"],
    }
    await db.model_versions.insert_one(metrics_doc.copy())
    await db.model_metrics.insert_one(metrics_doc.copy())
    await db.training_logs.insert_one({
        "type": "training",
        "status": "completed",
        "model_version": artifact["model_version"],
        "algorithm": artifact["best_name"],
        "promoted": promoted,
        "duration_seconds": result["duration_seconds"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    try:
        from model_loader_service import load_production_model

        load_production_model()
    except Exception:
        logger.exception("Unable to reload production model after training.")
    return metrics_doc


async def latest_model_metrics(db) -> Dict[str, Any]:
    doc = await db.model_metrics.find_one(sort=[("training_date", -1)])
    if not doc:
        return {"trained": False}
    doc = dict(doc)
    doc.pop("_id", None)
    doc["trained"] = True
    return doc


async def training_history(db, limit: int = 50) -> List[Dict[str, Any]]:
    cursor = db.training_logs.find({}).sort("created_at", -1).limit(limit)
    rows = []
    async for row in cursor:
        row = dict(row)
        row["id"] = str(row.pop("_id"))
        rows.append(row)
    return rows


async def training_status(db) -> Dict[str, Any]:
    latest_log = await db.training_logs.find_one(sort=[("created_at", -1)])
    latest_collection = await db.training_logs.find_one({"type": "collection"}, sort=[("created_at", -1)])
    latest_training = await db.training_logs.find_one({"type": "training"}, sort=[("created_at", -1)])
    status = {
        "latest_log": dict(latest_log) if latest_log else None,
        "latest_collection": dict(latest_collection) if latest_collection else None,
        "latest_training": dict(latest_training) if latest_training else None,
        "training_rows": await db.training_dataset.count_documents({}),
        "historical_rows": await db.historical_environment.count_documents({}),
    }
    for key in ("latest_log", "latest_collection", "latest_training"):
        if status[key] and "_id" in status[key]:
            status[key]["id"] = str(status[key].pop("_id"))
    return status


async def dataset_statistics(db) -> Dict[str, Any]:
    total = await db.training_dataset.count_documents({})
    historical = await db.historical_environment.count_documents({})
    pipeline = [
        {"$group": {"_id": "$city", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    cities = [{"city": row["_id"], "count": row["count"]} async for row in db.training_dataset.aggregate(pipeline)]
    latest = await db.training_dataset.find_one(sort=[("timestamp", -1)])
    earliest = await db.training_dataset.find_one(sort=[("timestamp", 1)])
    return {
        "training_rows": total,
        "historical_rows": historical,
        "cities": cities,
        "earliest_timestamp": (earliest or {}).get("timestamp"),
        "latest_timestamp": (latest or {}).get("timestamp"),
    }


async def feature_importance(db) -> List[Dict[str, Any]]:
    doc = await db.model_metrics.find_one(sort=[("training_date", -1)])
    if not doc:
        return []
    return doc.get("feature_importance", [])
