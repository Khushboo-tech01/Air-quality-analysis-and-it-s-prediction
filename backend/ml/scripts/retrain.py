"""One-command AeroPulse AutoML retraining pipeline.

Run from ``backend/ml/scripts`` or the repository root:

    python backend/ml/scripts/retrain.py
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from download_dataset import main as download_dataset
from evaluate_models import write_evaluation_reports
from feature_engineering import engineer_features
from preprocess import preprocess
from select_best_model import update_metrics
from train_models import train_all
from utils import REPORTS_DIR, configure_logging, ensure_dirs


def build_pdf_report(metrics: dict) -> str | None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
        from reportlab.lib.styles import getSampleStyleSheet
    except Exception:
        return None

    path = REPORTS_DIR / "automl_training_report.pdf"
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    story = [
        Paragraph("AeroPulse AutoML Training Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Version: {metrics['version']}", styles["Normal"]),
        Paragraph(f"Best Algorithm: {metrics['algorithm']}", styles["Normal"]),
        Paragraph(f"Dataset Size: {metrics['dataset_size']}", styles["Normal"]),
        Spacer(1, 12),
    ]
    rows = [["Rank", "Algorithm", "RMSE", "MAE", "R2", "MAPE", "Training Time"]]
    for index, row in enumerate(metrics["leaderboard"], start=1):
        rows.append([index, row["algorithm"], row["rmse"], row["mae"], row["r2"], row["mape"], row["training_time_seconds"]])
    story.append(Table(rows))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Top Features", styles["Heading2"]))
    feature_rows = [["Feature", "Importance"]] + [[item["feature"], item["importance"]] for item in metrics.get("feature_importance", [])[:20]]
    story.append(Table(feature_rows))
    doc.build(story)
    return str(path)


def main() -> dict:
    logger = configure_logging()
    ensure_dirs()
    logger.info("Starting AeroPulse AutoML retraining pipeline.")
    data_result = download_dataset()
    preprocess()
    engineer_features()
    training_result = train_all()
    reports = write_evaluation_reports(training_result)
    metrics = update_metrics(training_result, reports, dataset_name=", ".join(data_result.get("raw_files", [])))
    pdf_path = build_pdf_report(metrics)
    if pdf_path:
        metrics["reports"]["pdf"] = pdf_path
    logger.info("AutoML retraining complete. Best model: %s | R2=%s | RMSE=%s", metrics["algorithm"], metrics["r2"], metrics["rmse"])
    return metrics


if __name__ == "__main__":
    main()
