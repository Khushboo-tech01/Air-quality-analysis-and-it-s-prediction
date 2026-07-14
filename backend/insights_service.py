"""Deterministic dataset insights without a third-party AI dependency."""
async def generate_insight(summary: dict, session_id: str = "") -> str:
    avg, peak, rows = summary.get("avg_aqi", 0), summary.get("max_aqi", 0), summary.get("rows", 0)
    if avg <= 50: guidance = "Air quality is generally good; continue monitoring local changes."
    elif avg <= 100: guidance = "Air quality is moderate; sensitive people may reduce prolonged exertion."
    elif avg <= 150: guidance = "Sensitive groups should limit extended outdoor activity."
    else: guidance = "Pollution warrants reducing outdoor exposure and following local health guidance."
    return f"Analysis of {rows:,} observations shows an average AQI of {avg} and a peak AQI of {peak}. {guidance}"
