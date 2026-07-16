"""Persist metadata for the selected AutoML winner."""
from __future__ import annotations

import pickle
from datetime import datetime, timezone
from typing import Any, Dict

from utils import BEST_MODEL, METRICS_JSON, REPORTS_DIR, git_commit, load_json, model_size_mb, save_json, version_id


def _feature_importance() -> list[dict]:
    if not BEST_MODEL.exists():
        return []
    with open(BEST_MODEL, "rb") as file:
        artifact = pickle.load(file)
    model = artifact["model"].named_steps.get("model")
    values = getattr(model, "feature_importances_", None)
    if values is None and hasattr(model, "coef_"):
        values = abs(model.coef_)
    if values is None:
        return []
    total = float(sum(abs(v) for v in values)) or 1.0
    rows = [
        {"feature": feature, "importance": round(float(abs(value) / total), 6)}
        for feature, value in zip(artifact.get("feature_keys", []), values)
    ]
    return sorted(rows, key=lambda item: item["importance"], reverse=True)[:20]


def update_metrics(training_result: Dict[str, Any], reports: Dict[str, str], dataset_name: str = "automl_raw_csv") -> Dict[str, Any]:
    winner = training_result["winner"]
    history = load_json(METRICS_JSON, {"history": []}).get("history", [])
    metadata = {
        "version": version_id(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "date": datetime.now(timezone.utc).date().isoformat(),
        "dataset_name": dataset_name,
        "dataset_size": training_result["dataset_size"],
        "training_duration_seconds": round(sum(row["training_time_seconds"] for row in training_result["leaderboard"]), 4),
        "git_commit": git_commit(),
        "algorithm": winner["algorithm"],
        "metrics": {key: winner[key] for key in ["rmse", "mae", "mse", "r2", "mape", "explained_variance"]},
        "rmse": winner["rmse"],
        "mae": winner["mae"],
        "mse": winner["mse"],
        "r2": winner["r2"],
        "mape": winner["mape"],
        "explained_variance": winner["explained_variance"],
        "training_time_seconds": winner["training_time_seconds"],
        "prediction_time_seconds": winner["prediction_time_seconds"],
        "model_size_mb": model_size_mb(BEST_MODEL),
        "feature_count": len(training_result["feature_keys"]),
        "feature_list": training_result["feature_keys"],
        "feature_importance": _feature_importance(),
        "leaderboard": training_result["leaderboard"],
        "reports": reports,
        "best_model_path": str(BEST_MODEL),
    }
    history.insert(0, metadata)
    payload = {**metadata, "history": history[:25]}
    save_json(payload, METRICS_JSON)
    save_json(payload, REPORTS_DIR / "training_summary.json")
    return payload


if __name__ == "__main__":
    raise SystemExit("Run retrain.py so model selection receives the in-memory training result.")
