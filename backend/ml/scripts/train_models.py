"""Train and evaluate all AeroPulse AutoML candidate models."""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor, StackingRegressor, VotingRegressor
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.model_selection import KFold, RandomizedSearchCV, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

from utils import BEST_MODEL, MODELS_DIR, TARGET_COLUMN, TRAIN_CSV, configure_logging, model_size_mb, regression_metrics, save_pickle, timer

try:
    from xgboost import XGBRegressor
except Exception:
    XGBRegressor = None

try:
    from catboost import CatBoostRegressor
except Exception:
    CatBoostRegressor = None

try:
    from lightgbm import LGBMRegressor
except Exception:
    LGBMRegressor = None


def feature_columns(frame: pd.DataFrame) -> list[str]:
    excluded = {TARGET_COLUMN, "date", "city", "state", "country", "dataset_name", "source_files"}
    return [column for column in frame.select_dtypes(include=[np.number]).columns if column not in excluded]


def candidates() -> Dict[str, Tuple[Any, Dict[str, list]]]:
    models: Dict[str, Tuple[Any, Dict[str, list]]] = {
        "Linear Regression": (LinearRegression(), {}),
        "Ridge": (Ridge(), {"model__alpha": [0.1, 1.0, 10.0, 30.0]}),
        "Lasso": (Lasso(max_iter=5000), {"model__alpha": [0.001, 0.01, 0.1, 1.0]}),
        "ElasticNet": (ElasticNet(max_iter=5000), {"model__alpha": [0.001, 0.01, 0.1, 1.0], "model__l1_ratio": [0.2, 0.5, 0.8]}),
        "Random Forest": (RandomForestRegressor(random_state=42, n_jobs=-1), {"model__n_estimators": [120, 220], "model__max_depth": [10, 18, None], "model__min_samples_leaf": [1, 3]}),
        "Extra Trees": (ExtraTreesRegressor(random_state=42, n_jobs=-1), {"model__n_estimators": [160, 260], "model__max_depth": [10, 18, None], "model__min_samples_leaf": [1, 2]}),
        "Gradient Boosting": (GradientBoostingRegressor(random_state=42), {"model__n_estimators": [120, 220], "model__learning_rate": [0.04, 0.08], "model__max_depth": [2, 3]}),
    }
    if XGBRegressor is not None:
        models["XGBoost"] = (XGBRegressor(random_state=42, objective="reg:squarederror", n_jobs=2), {"model__n_estimators": [160, 260], "model__max_depth": [3, 5], "model__learning_rate": [0.04, 0.08]})
    if CatBoostRegressor is not None:
        models["CatBoost"] = (CatBoostRegressor(random_state=42, verbose=False), {"model__depth": [4, 6], "model__learning_rate": [0.04, 0.08], "model__iterations": [200, 350]})
    if LGBMRegressor is not None:
        models["LightGBM"] = (LGBMRegressor(random_state=42, n_jobs=-1), {"model__n_estimators": [160, 260], "model__num_leaves": [31, 63], "model__learning_rate": [0.04, 0.08]})
    models["Voting Regressor"] = (
        VotingRegressor([
            ("rf", RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=-1)),
            ("et", ExtraTreesRegressor(n_estimators=160, random_state=42, n_jobs=-1)),
            ("gb", GradientBoostingRegressor(random_state=42)),
        ]),
        {},
    )
    models["Stacking Regressor"] = (
        StackingRegressor(
            estimators=[
                ("rf", RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)),
                ("et", ExtraTreesRegressor(n_estimators=120, random_state=42, n_jobs=-1)),
            ],
            final_estimator=Ridge(),
            n_jobs=-1,
        ),
        {},
    )
    return models


def _artifact_name(name: str) -> str:
    return name.lower().replace(" ", "_") + ".pkl"


def train_all() -> Dict[str, Any]:
    logger = configure_logging()
    frame = pd.read_csv(TRAIN_CSV)
    keys = feature_columns(frame)
    X = frame[keys]
    y = frame[TARGET_COLUMN].clip(0, 500)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    leaderboard = []
    artifacts: Dict[str, Dict] = {}

    for name, (estimator, params) in candidates().items():
        logger.info("Training %s", name)
        started, elapsed = timer()
        pipeline = Pipeline([("scaler", RobustScaler()), ("model", estimator)])
        if params:
            search = RandomizedSearchCV(
                pipeline,
                params,
                n_iter=min(8, max(1, int(np.prod([len(v) for v in params.values()])))),
                scoring="neg_root_mean_squared_error",
                cv=cv,
                n_jobs=1,
                random_state=42,
            )
            search.fit(X_train, y_train)
            best_estimator = search.best_estimator_
            best_params = search.best_params_
        else:
            pipeline.fit(X_train, y_train)
            best_estimator = pipeline
            best_params = {}
        training_time = elapsed()
        predict_started = time.perf_counter()
        predictions = np.clip(best_estimator.predict(X_test), 0, 500)
        prediction_time = round(time.perf_counter() - predict_started, 4)
        metrics = regression_metrics(y_test, predictions)
        cv_scores = -cross_val_score(best_estimator, X_train, y_train, scoring="neg_root_mean_squared_error", cv=cv, n_jobs=1)
        model_path = MODELS_DIR / _artifact_name(name)
        artifact = {
            "model": best_estimator,
            "algorithm": name,
            "feature_keys": keys,
            "metrics": metrics,
            "best_metrics": metrics,
            "best_params": best_params,
            "cv_rmse_scores": [round(float(score), 4) for score in cv_scores],
            "cv_rmse_mean": round(float(np.mean(cv_scores)), 4),
            "means": X.mean(numeric_only=True).to_dict(),
            "stds": X.std(numeric_only=True).replace(0, 1).fillna(1).to_dict(),
            "dataset_rows": int(len(frame)),
            "trained_at": time.time(),
        }
        save_pickle(artifact, model_path)
        row = {
            "algorithm": name,
            **metrics,
            "cv_rmse": artifact["cv_rmse_mean"],
            "training_time_seconds": training_time,
            "prediction_time_seconds": prediction_time,
            "model_size_mb": model_size_mb(model_path),
            "model_path": str(model_path),
            "best_params": best_params,
        }
        leaderboard.append(row)
        artifacts[name] = artifact

    leaderboard = sorted(leaderboard, key=lambda row: (-row["r2"], row["rmse"], row["mae"], row["mape"]))
    winner = leaderboard[0]
    shutil.copyfile(winner["model_path"], BEST_MODEL)
    logger.info("Selected best model: %s", winner["algorithm"])
    return {"leaderboard": leaderboard, "winner": winner, "feature_keys": keys, "dataset_size": len(frame)}


if __name__ == "__main__":
    train_all()
