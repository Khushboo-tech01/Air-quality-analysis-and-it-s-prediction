"""PDF report generation."""
import io
from datetime import datetime, timezone
from typing import Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H", fontSize=22, leading=26, textColor=colors.HexColor("#111111"),
                              spaceAfter=12, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Sub", fontSize=11, textColor=colors.HexColor("#4b5563"),
                              spaceAfter=18))
    styles.add(ParagraphStyle(name="Section", fontSize=14, leading=18, textColor=colors.HexColor("#2563EB"),
                              spaceBefore=14, spaceAfter=8, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Body", fontSize=10, leading=14, textColor=colors.HexColor("#1f2937")))
    return styles


def _basic_table(rows: List[List[str]], col_widths: List[float]) -> Table:
    table = Table(rows, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#0f172a")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def build_prediction_pdf(prediction: Dict, user_email: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm)
    styles = _styles()
    story = [
        Paragraph("AI AQI Forecast Report", styles["H"]),
        Paragraph(f"Generated for {user_email} on {datetime.now(timezone.utc).strftime('%b %d, %Y %H:%M UTC')}", styles["Sub"]),
        Paragraph("Forecast Summary", styles["Section"]),
    ]

    story.append(_basic_table([
        ["Tomorrow AQI", str(prediction.get("aqi", "-"))],
        ["Tomorrow Category", prediction.get("category", "-")],
        ["Tomorrow Health Advice", prediction.get("advice", "-")],
        ["Model Used", prediction.get("model", "-")],
        ["Location", prediction.get("location", "-")],
        ["Generated Date", prediction.get("date", "-")],
    ], [55 * mm, 115 * mm]))
    story.append(Spacer(1, 12))

    current = prediction.get("current_conditions") or prediction.get("inputs") or {}
    if current:
        story.append(Paragraph("Current Conditions", styles["Section"]))
        story.append(_basic_table([[k.upper(), str(v)] for k, v in current.items()], [55 * mm, 115 * mm]))

    forecast = prediction.get("forecast") or []
    if forecast:
        story.append(Paragraph("7-Day Forecast", styles["Section"]))
        forecast_rows = [["Day", "AQI", "Category", "Risk", "Confidence", "Weather"]]
        forecast_rows.extend([
            [
                item.get("label", "-"),
                str(item.get("predicted_aqi", item.get("aqi", "-"))),
                item.get("category", "-"),
                item.get("risk", "-"),
                f"{item.get('confidence', '-')}%",
                item.get("weather_summary", "-"),
            ]
            for item in forecast
        ])
        forecast_table = Table(forecast_rows, colWidths=[25 * mm, 18 * mm, 42 * mm, 24 * mm, 25 * mm, 36 * mm])
        forecast_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(forecast_table)

        story.append(Paragraph("Forecast Chart", styles["Section"]))
        sparkline = " -> ".join(f"{item.get('label')}: {item.get('predicted_aqi', item.get('aqi', '-'))}" for item in forecast)
        story.append(Paragraph(sparkline, styles["Body"]))

        story.append(Paragraph("Health Advice", styles["Section"]))
        advice = " ".join(f"{item.get('label')}: {item.get('health_advice', '-')}" for item in forecast)
        story.append(Paragraph(advice, styles["Body"]))

    story.append(Spacer(1, 20))
    story.append(Paragraph("This report was generated by AeroPulse - AI Air Quality Forecasting Platform.", styles["Body"]))
    doc.build(story)
    buf.seek(0)
    return buf.read()


def build_model_metrics_pdf(dataset_name: str, results: List[Dict], best_model: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm)
    styles = _styles()
    story = [
        Paragraph("Model Performance Report", styles["H"]),
        Paragraph(f"Dataset: {dataset_name}", styles["Sub"]),
        Paragraph(f"Best Model: {best_model}", styles["Section"]),
    ]
    header = ["Model", "RMSE", "MAE", "R2", "CV R2", "Train (ms)", "Predict (ms)"]
    body_rows = [header] + [[r["name"], r["rmse"], r["mae"], r["r2"], r["cv_r2"], r["train_ms"], r["predict_ms"]] for r in results]
    table = Table(body_rows, colWidths=[45 * mm, 20 * mm, 20 * mm, 20 * mm, 20 * mm, 22 * mm, 25 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    doc.build(story)
    buf.seek(0)
    return buf.read()
