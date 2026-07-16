"""Generate visual and tabular AutoML evaluation reports."""
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from utils import REPORTS_DIR, configure_logging


def write_evaluation_reports(training_result: Dict[str, Any]) -> Dict[str, str]:
    logger = configure_logging()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    leaderboard = pd.DataFrame(training_result["leaderboard"])
    leaderboard_path = REPORTS_DIR / "leaderboard.csv"
    leaderboard.to_csv(leaderboard_path, index=False)

    chart_paths: Dict[str, str] = {"leaderboard": str(leaderboard_path)}
    try:
        import matplotlib.pyplot as plt

        for metric in ["rmse", "mae", "mape", "r2", "training_time_seconds", "prediction_time_seconds"]:
            ax = leaderboard.plot(kind="bar", x="algorithm", y=metric, legend=False, figsize=(10, 5), title=f"{metric.upper()} Comparison")
            ax.set_xlabel("Algorithm")
            ax.set_ylabel(metric)
            plt.tight_layout()
            path = REPORTS_DIR / f"{metric}_comparison.png"
            plt.savefig(path)
            plt.close()
            chart_paths[metric] = str(path)
    except Exception as exc:
        logger.warning("Chart generation skipped: %s", exc)
    return chart_paths


if __name__ == "__main__":
    raise SystemExit("Run retrain.py so evaluation receives the in-memory training result.")
