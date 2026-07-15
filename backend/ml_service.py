"""ML Service — trains multiple regressors on a dataset and returns metrics."""
import time
import pickle
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor

from aqi_utils import detect_schema
from eda_service import ensure_aqi

MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Canonical feature keys used at prediction time
CANONICAL_FEATURES: List[str] = ["pm25", "pm10", "no2", "so2", "co", "o3", "temp", "humidity", "wind", "pressure"]


def _select_feature_frame(df: pd.DataFrame, schema: Dict) -> tuple[pd.DataFrame, List[str], Dict[str, float]]:
    used_cols: List[str] = []
    key_order: List[str] = []
    for k in CANONICAL_FEATURES:
        col = schema["features"].get(k)
        if col and col in df.columns and col not in used_cols:
            used_cols.append(col)
            key_order.append(k)
    if not used_cols:
        raise ValueError("Dataset has no recognisable pollutant/weather columns.")
    X = df[used_cols].apply(pd.to_numeric, errors="coerce")
    X.columns = key_order
    means: Dict[str, float] = {}
    for key in key_order:
        mean = X[key].mean()
        means[key] = float(mean) if pd.notna(mean) else 0.0
    X = X.fillna(pd.Series(means))
    return X, key_order, means


def build_models() -> Dict[str, object]:
    return {
        "Linear Regression":  LinearRegression(),
        "Decision Tree":      DecisionTreeRegressor(max_depth=10, random_state=42),
        "Random Forest":      RandomForestRegressor(n_estimators=80, max_depth=14, random_state=42, n_jobs=-1),
        "Gradient Boosting":  GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42),
        "XGBoost":            XGBRegressor(n_estimators=120, max_depth=6, learning_rate=0.1, random_state=42, n_jobs=-1, verbosity=0),
    }


def train_all(csv_path: str, dataset_id: str) -> Dict:
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    schema = detect_schema(list(df.columns))
    df = ensure_aqi(df, schema)

    X, feature_keys, means = _select_feature_frame(df, schema)
    y = df["AQI"]

    # sub-sample very large datasets to keep training snappy
    if len(X) > 20_000:
        idx = np.random.default_rng(42).choice(len(X), 20_000, replace=False)
        X = X.iloc[idx].reset_index(drop=True)
        y = y.iloc[idx].reset_index(drop=True)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results: List[Dict] = []
    trained_models: Dict[str, object] = {}
    for name, mdl in build_models().items():
        t0 = time.perf_counter()
        mdl.fit(X_train, y_train)
        train_ms = round((time.perf_counter() - t0) * 1000, 1)

        t1 = time.perf_counter()
        preds = mdl.predict(X_test)
        pred_ms = round((time.perf_counter() - t1) * 1000, 1)

        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        mae  = float(mean_absolute_error(y_test, preds))
        r2   = float(r2_score(y_test, preds))
        # cross-validation on smaller sample for speed
        cv_sample = min(2000, len(X_train))
        try:
            cv = float(np.mean(cross_val_score(mdl, X_train.iloc[:cv_sample], y_train.iloc[:cv_sample],
                                               cv=3, scoring="r2")))
        except Exception:
            cv = 0.0

        trained_models[name] = mdl
        results.append({
            "name": name,
            "rmse": round(rmse, 3),
            "mae":  round(mae, 3),
            "r2":   round(r2, 4),
            "cv_r2":round(cv, 4),
            "train_ms": train_ms,
            "predict_ms": pred_ms,
        })

    # Best model by highest R²
    best = max(results, key=lambda r: r["r2"])
    best_model = trained_models[best["name"]]
    best_test_predictions = best_model.predict(X_test)
    residual_std = float(np.std(y_test.to_numpy() - best_test_predictions))
    artifact = {
        "model": best_model,
        "feature_keys": feature_keys,
        "means": means,
        "stds": {k: float(X[k].std()) if float(X[k].std() or 0) > 0 else 1.0 for k in feature_keys},
        "best_name": best["name"],
        "best_metrics": best,
        "dataset_rows": int(len(X)),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_version": f"{dataset_id[:8]}-{int(time.time())}",
        "residual_std": residual_std,
        "target_std": float(y.std()) if float(y.std() or 0) > 0 else 1.0,
        "schema": schema,
    }
    path = MODELS_DIR / f"{dataset_id}.pkl"
    with open(path, "wb") as f:
        pickle.dump(artifact, f)

    return {
        "results": results,
        "best_model": best["name"],
        "feature_keys": feature_keys,
        "model_path": str(path),
        "rows_used": int(len(X)),
    }


def predict_from_model(dataset_id: str, feature_input: Dict[str, float]) -> Dict:
    path = MODELS_DIR / f"{dataset_id}.pkl"
    if not path.exists():
        raise FileNotFoundError("Model not trained yet for this dataset")
    with open(path, "rb") as f:
        art = pickle.load(f)
    keys: List[str] = art["feature_keys"]
    means: Dict[str, float] = art["means"]
    stds: Dict[str, float] = art.get("stds", {})
    row = [float(feature_input.get(k, means.get(k, 0.0))) for k in keys]
    x = pd.DataFrame([row], columns=keys)
    pred = float(art["model"].predict(x)[0])
    pred = max(0.0, min(500.0, pred))
    metrics = art.get("best_metrics", {})
    r2_confidence = max(0.0, min(1.0, float(metrics.get("r2", 0.0))))
    z_scores = [
        abs(float(x.iloc[0][k]) - float(means.get(k, 0.0))) / max(float(stds.get(k, 1.0)), 1e-6)
        for k in keys
    ]
    drift_penalty = min(0.35, float(np.mean(z_scores)) * 0.08) if z_scores else 0.0
    interval_penalty = min(
        0.25,
        float(art.get("residual_std", 0.0)) / max(float(art.get("target_std", 1.0)), 1e-6) * 0.15,
    )
    confidence = max(0.0, min(0.99, r2_confidence - drift_penalty - interval_penalty))
    return {
        "prediction": pred,
        "model": art["best_name"],
        "features_used": keys,
        "confidence": round(confidence * 100, 1),
        "metrics": metrics,
        "model_version": art.get("model_version"),
        "trained_at": art.get("trained_at"),
        "dataset_rows": art.get("dataset_rows"),
        "prediction_interval": {
            "low": round(max(0.0, pred - 1.96 * float(art.get("residual_std", 0.0))), 1),
            "high": round(min(500.0, pred + 1.96 * float(art.get("residual_std", 0.0))), 1),
        },
    }


def forecast_next_days(dataset_id: str, csv_path: str, days: int = 7) -> List[Dict]:
    """Forecast future AQI from trend-adjusted pollutant projections."""
    path = MODELS_DIR / f"{dataset_id}.pkl"
    if not path.exists():
        raise FileNotFoundError("Model not trained yet for this dataset")
    with open(path, "rb") as f:
        art = pickle.load(f)
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    schema = art["schema"]
    keys = art["feature_keys"]
    means = art["means"]

    last_values: Dict[str, float] = {}
    trend_values: Dict[str, float] = {}
    for k in keys:
        col = schema["features"].get(k)
        if col and col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            last_values[k] = float(series.iloc[-1]) if not series.empty else means.get(k, 0.0)
            if len(series) >= 7:
                recent = series.tail(7).to_numpy()
                trend_values[k] = float((recent[-1] - recent[0]) / max(len(recent) - 1, 1))
            else:
                trend_values[k] = 0.0
        else:
            last_values[k] = means.get(k, 0.0)
            trend_values[k] = 0.0

    rng = np.random.default_rng(42)
    forecasts = []
    for i in range(1, days + 1):
        projected = {
            k: max(0.0, last_values[k] + trend_values[k] * i + last_values[k] * rng.normal(0, 0.025))
            for k in keys
        }
        x = pd.DataFrame([[projected[k] for k in keys]], columns=keys)
        pred = float(art["model"].predict(x)[0])
        pred = max(0.0, min(500.0, pred))
        forecasts.append({"day": i, "aqi": round(pred, 1), "features": {k: round(v, 3) for k, v in projected.items()}})
    return forecasts
