"""EDA — exploratory data analysis computations."""
import numpy as np
import pandas as pd
from typing import Dict, List

from aqi_utils import detect_schema, pm25_to_aqi


def load_dataset_df(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    return df


def ensure_aqi(df: pd.DataFrame, schema: Dict) -> pd.DataFrame:
    """Guarantee an 'AQI' column exists in the dataframe."""
    if schema.get("target") and schema["target"] in df.columns:
        df["AQI"] = pd.to_numeric(df[schema["target"]], errors="coerce")
    elif schema["features"].get("pm25") and schema["features"]["pm25"] in df.columns:
        pm = pd.to_numeric(df[schema["features"]["pm25"]], errors="coerce").fillna(0)
        df["AQI"] = pm.apply(pm25_to_aqi)
    else:
        # No target and no PM2.5 — fall back to a synthetic value from any pollutant
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if num_cols:
            df["AQI"] = df[num_cols].mean(axis=1)
        else:
            df["AQI"] = 0.0
    df["AQI"] = pd.to_numeric(df["AQI"], errors="coerce").fillna(0).clip(0, 500)
    return df


def dataset_preview(df: pd.DataFrame, n: int = 20) -> Dict:
    head = df.head(n).replace({np.nan: None}).to_dict(orient="records")
    dtypes = {c: str(df[c].dtype) for c in df.columns}
    missing = df.isna().sum().to_dict()
    missing = {k: int(v) for k, v in missing.items()}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    stats = {}
    if numeric_cols:
        desc = df[numeric_cols].describe().round(2).replace({np.nan: None}).to_dict()
        stats = desc
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "dtypes": dtypes,
        "missing": missing,
        "preview": head,
        "stats": stats,
    }


def histogram(df: pd.DataFrame, column: str, bins: int = 20) -> Dict:
    s = pd.to_numeric(df[column], errors="coerce").dropna()
    if s.empty:
        return {"bins": [], "counts": []}
    counts, edges = np.histogram(s, bins=bins)
    labels = [f"{round(edges[i], 1)}–{round(edges[i+1], 1)}" for i in range(len(counts))]
    return {"bins": labels, "counts": counts.tolist()}


def correlation_matrix(df: pd.DataFrame) -> Dict:
    num_df = df.select_dtypes(include=[np.number])
    if num_df.shape[1] < 2:
        return {"labels": [], "matrix": []}
    corr = num_df.corr().round(2).replace({np.nan: 0}).values.tolist()
    return {"labels": num_df.columns.tolist(), "matrix": corr}


def aqi_distribution(df: pd.DataFrame) -> List[Dict]:
    from aqi_utils import AQI_CATEGORIES
    buckets = []
    for cat in AQI_CATEGORIES:
        n = int(((df["AQI"] >= cat["low"]) & (df["AQI"] <= cat["high"])).sum())
        buckets.append({"category": cat["label"], "count": n, "color": cat["color"]})
    return buckets


def monthly_trend(df: pd.DataFrame, date_col: str | None) -> List[Dict]:
    if not date_col or date_col not in df.columns:
        return []
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    if d.empty:
        return []
    d["month"] = d[date_col].dt.to_period("M").astype(str)
    grouped = d.groupby("month")["AQI"].mean().round(1).reset_index()
    return grouped.to_dict(orient="records")


def yearly_trend(df: pd.DataFrame, date_col: str | None) -> List[Dict]:
    if not date_col or date_col not in df.columns:
        return []
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    if d.empty:
        return []
    d["year"] = d[date_col].dt.year
    grouped = d.groupby("year")["AQI"].mean().round(1).reset_index()
    grouped["year"] = grouped["year"].astype(int)
    return grouped.to_dict(orient="records")


def pollutant_comparison(df: pd.DataFrame, schema: Dict) -> List[Dict]:
    result = []
    for key, col in schema["features"].items():
        if col and col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            if not s.empty:
                result.append({"pollutant": key.upper(), "mean": round(float(s.mean()), 2), "max": round(float(s.max()), 2)})
    return result


def clean_dataset(df: pd.DataFrame) -> Dict:
    """Return a cleaning report (does not mutate)."""
    before = len(df)
    duplicates = int(df.duplicated().sum())
    nulls = int(df.isna().sum().sum())
    # Outlier count by IQR on numeric columns
    numeric = df.select_dtypes(include=[np.number])
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    outliers = int(((numeric < (q1 - 1.5 * iqr)) | (numeric > (q3 + 1.5 * iqr))).sum().sum())
    cleaned = df.drop_duplicates().copy()
    # Fill numeric NaN with mean
    for c in cleaned.select_dtypes(include=[np.number]).columns:
        cleaned[c] = cleaned[c].fillna(cleaned[c].mean())
    # Fill object NaN with "Unknown"
    for c in cleaned.select_dtypes(include=["object"]).columns:
        cleaned[c] = cleaned[c].fillna("Unknown")
    return {
        "rows_before": before,
        "rows_after": len(cleaned),
        "duplicates_removed": duplicates,
        "nulls_filled": nulls,
        "outliers_detected": outliers,
    }


def feature_engineering_report(df: pd.DataFrame, date_col: str | None) -> Dict:
    engineered: List[str] = []
    if date_col and date_col in df.columns:
        d = pd.to_datetime(df[date_col], errors="coerce")
        engineered += ["year", "month", "day_of_week", "is_weekend", "season"]
    if "AQI" in df.columns:
        engineered += ["AQI_lag_1", "AQI_rolling_7"]
    return {"created_features": engineered, "count": len(engineered)}
