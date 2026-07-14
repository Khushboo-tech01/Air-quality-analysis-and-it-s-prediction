"""AeroPulse — AQI Analysis & Prediction backend (FastAPI)."""
from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field
import pandas as pd
import io

from auth import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, get_current_user, get_current_admin, seed_admin,
)
from aqi_utils import classify_aqi, detect_schema, pm25_to_aqi
from eda_service import (
    load_dataset_df, ensure_aqi, dataset_preview, histogram, correlation_matrix,
    aqi_distribution, monthly_trend, yearly_trend, pollutant_comparison,
    clean_dataset, feature_engineering_report,
)
from ml_service import train_all, predict_from_model, forecast_next_days, CANONICAL_FEATURES
from reports_service import build_prediction_pdf, build_model_metrics_pdf
from insights_service import generate_insight
from sample_data import generate_sample_csv

# ────────────────────────────────────────────────────────────────────────────
# MongoDB
# ────────────────────────────────────────────────────────────────────────────
mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
db = client[os.environ.get("DB_NAME", "aeropulse")]

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("aeropulse")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


# ────────────────────────────────────────────────────────────────────────────
# FastAPI
# ────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="AeroPulse API", version="1.0.0")
api = APIRouter(prefix="/api")


@app.on_event("startup")
async def _startup():
    await db.users.create_index("email", unique=True)
    await db.datasets.create_index("user_id")
    await db.predictions.create_index("user_id")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.login_attempts.create_index("identifier")
    await seed_admin(db)
    logger.info("Startup complete — admin seeded, indexes ensured.")


@app.on_event("shutdown")
async def _shutdown():
    client.close()


# ────────────────────────────────────────────────────────────────────────────
# Utility
# ────────────────────────────────────────────────────────────────────────────
def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


def _serialize(doc: dict) -> dict:
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    # Convert any remaining ObjectId fields to strings
    for k, v in list(doc.items()):
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    doc.pop("password_hash", None)
    return doc


# ────────────────────────────────────────────────────────────────────────────
# AUTH
# ────────────────────────────────────────────────────────────────────────────
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1, max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=6)

class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)

class PasswordIn(BaseModel):
    password: str = Field(min_length=6)


@api.post("/auth/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    doc = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "name": payload.name.strip(),
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.users.insert_one(doc)
    uid = str(result.inserted_id)
    set_auth_cookies(response, create_access_token(uid, email), create_refresh_token(uid))
    user = await db.users.find_one({"_id": result.inserted_id})
    return _serialize(user)


@api.post("/auth/login")
async def login(payload: LoginIn, request: Request, response: Response):
    email = payload.email.lower()
    identifier = email  # key by email only — ingress uses multiple pod IPs

    # brute force check
    attempts = await db.login_attempts.find_one({"identifier": identifier})
    if attempts and attempts.get("count", 0) >= 5:
        locked_at = attempts.get("locked_at")
        if locked_at and (datetime.now(timezone.utc).timestamp() - locked_at) < 900:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$inc": {"count": 1}, "$set": {"locked_at": datetime.now(timezone.utc).timestamp()}},
            upsert=True,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await db.login_attempts.delete_one({"identifier": identifier})
    uid = str(user["_id"])
    set_auth_cookies(response, create_access_token(uid, email), create_refresh_token(uid))
    return _serialize(user)


@api.post("/auth/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


@api.post("/auth/guest")
async def guest_login(response: Response):
    """Auto-login as the shared guest user — enables the no-login-page UX."""
    user = await db.users.find_one({"email": "guest@aqi.io"})
    if not user:
        raise HTTPException(status_code=500, detail="Guest account is not seeded")
    uid = str(user["_id"])
    set_auth_cookies(response, create_access_token(uid, user["email"]), create_refresh_token(uid))
    return _serialize(user)


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return user


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    import jwt
    from auth import JWT_ALGORITHM, _secret
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        uid = payload["sub"]
        user = await db.users.find_one({"_id": ObjectId(uid)})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        set_auth_cookies(response, create_access_token(uid, user["email"]), create_refresh_token(uid))
        return {"ok": True}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@api.post("/auth/forgot-password")
async def forgot(payload: ForgotIn):
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    # Always return ok (don't leak account existence)
    if user:
        token = secrets.token_urlsafe(32)
        from datetime import timedelta
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.password_reset_tokens.insert_one({
            "user_id": user["_id"], "token": token, "used": False, "expires_at": expires
        })
        logger.info(f"[password reset] token for {email}: {token}")
    return {"ok": True, "message": "If this account exists, a reset link has been logged."}


@api.post("/auth/reset-password")
async def reset(payload: ResetIn):
    doc = await db.password_reset_tokens.find_one({"token": payload.token, "used": False})
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if doc["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")
    await db.users.update_one({"_id": doc["user_id"]}, {"$set": {"password_hash": hash_password(payload.password)}})
    await db.password_reset_tokens.update_one({"_id": doc["_id"]}, {"$set": {"used": True}})
    return {"ok": True}

@api.patch("/auth/profile")
async def update_profile(payload: ProfileIn, user=Depends(get_current_user)):
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"name": payload.name.strip()}})
    return {**user, "name": payload.name.strip()}

@api.post("/auth/change-password")
async def change_password(payload: PasswordIn, user=Depends(get_current_user)):
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"password_hash": hash_password(payload.password)}})
    return {"ok": True}

@api.delete("/auth/account")
async def delete_account(response: Response, user=Depends(get_current_user)):
    uid = ObjectId(user["id"])
    cursor = db.datasets.find({"user_id": uid})
    async for dataset in cursor:
        try: Path(dataset.get("path", "")).unlink(missing_ok=True)
        except OSError: pass
    await db.datasets.delete_many({"user_id": uid})
    await db.predictions.delete_many({"user_id": uid})
    await db.users.delete_one({"_id": uid})
    clear_auth_cookies(response)
    return {"ok": True}


# ────────────────────────────────────────────────────────────────────────────
# DATASETS
# ────────────────────────────────────────────────────────────────────────────
@api.post("/datasets/upload")
async def upload_dataset(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Max upload size is 25 MB")
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")
    df.columns = [c.strip() for c in df.columns]
    schema = detect_schema(list(df.columns))

    doc = {
        "user_id": ObjectId(user["id"]),
        "name": file.filename,
        "rows": int(len(df)),
        "columns": list(df.columns),
        "schema": schema,
        "size_bytes": len(content),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "trained": False,
    }
    result = await db.datasets.insert_one(doc)
    dataset_id = str(result.inserted_id)
    file_path = UPLOAD_DIR / f"{dataset_id}.csv"
    file_path.write_bytes(content)
    await db.datasets.update_one({"_id": result.inserted_id}, {"$set": {"path": str(file_path)}})

    df = ensure_aqi(df, schema)
    return {"id": dataset_id, "name": file.filename, "schema": schema, **dataset_preview(df)}


@api.post("/datasets/seed-sample")
async def seed_sample(user=Depends(get_current_user)):
    """Generate a synthetic Indian-cities dataset for this user."""
    tmp_path = UPLOAD_DIR / f"sample_{user['id']}.csv"
    generate_sample_csv(tmp_path, days=180)
    df = pd.read_csv(tmp_path)
    schema = detect_schema(list(df.columns))
    doc = {
        "user_id": ObjectId(user["id"]),
        "name": "Sample_India_AQI_180days.csv",
        "rows": int(len(df)),
        "columns": list(df.columns),
        "schema": schema,
        "size_bytes": tmp_path.stat().st_size,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "trained": False,
    }
    result = await db.datasets.insert_one(doc)
    dataset_id = str(result.inserted_id)
    final_path = UPLOAD_DIR / f"{dataset_id}.csv"
    tmp_path.rename(final_path)
    await db.datasets.update_one({"_id": result.inserted_id}, {"$set": {"path": str(final_path)}})
    return {"id": dataset_id, "name": doc["name"], "rows": doc["rows"]}


@api.get("/datasets")
async def list_datasets(user=Depends(get_current_user)):
    cursor = db.datasets.find({"user_id": ObjectId(user["id"])}).sort("created_at", -1)
    items = []
    async for d in cursor:
        d = _serialize(d)
        d.pop("user_id", None)
        items.append(d)
    return items


@api.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = load_dataset_df(d["path"])
    df = ensure_aqi(df, d["schema"])
    out = _serialize(d)
    out.update(dataset_preview(df))
    return out


@api.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    try:
        Path(d["path"]).unlink(missing_ok=True)
    except Exception:
        pass
    model_path = ROOT_DIR / "models" / f"{dataset_id}.pkl"
    try:
        model_path.unlink(missing_ok=True)
    except Exception:
        pass
    await db.datasets.delete_one({"_id": d["_id"]})
    return {"ok": True}


# ────────────────────────────────────────────────────────────────────────────
# EDA
# ────────────────────────────────────────────────────────────────────────────
@api.get("/datasets/{dataset_id}/eda")
async def eda(dataset_id: str, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = load_dataset_df(d["path"])
    df = ensure_aqi(df, d["schema"])
    schema = d["schema"]
    hist_cols: List[str] = []
    for k in ("pm25", "pm10", "no2", "o3"):
        if schema["features"].get(k):
            hist_cols.append(schema["features"][k])
    if "AQI" in df.columns and "AQI" not in hist_cols:
        hist_cols.append("AQI")

    hists = {c: histogram(df, c) for c in hist_cols}

    location_avg: List[Dict[str, Any]] = []
    loc_col = schema.get("location")
    if loc_col and loc_col in df.columns:
        grp = df.groupby(loc_col)["AQI"].mean().round(1).reset_index()
        grp.columns = ["location", "avg_aqi"]
        location_avg = grp.sort_values("avg_aqi", ascending=False).to_dict(orient="records")

    return {
        "histograms": hists,
        "correlation": correlation_matrix(df),
        "aqi_distribution": aqi_distribution(df),
        "monthly_trend": monthly_trend(df, schema.get("date")),
        "yearly_trend": yearly_trend(df, schema.get("date")),
        "pollutant_comparison": pollutant_comparison(df, schema),
        "location_avg": location_avg,
    }


@api.post("/datasets/{dataset_id}/clean")
async def clean(dataset_id: str, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = load_dataset_df(d["path"])
    return clean_dataset(df)


@api.post("/datasets/{dataset_id}/feature-engineering")
async def feature_eng(dataset_id: str, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = load_dataset_df(d["path"])
    return feature_engineering_report(df, d["schema"].get("date"))


# ────────────────────────────────────────────────────────────────────────────
# MACHINE LEARNING
# ────────────────────────────────────────────────────────────────────────────
@api.post("/datasets/{dataset_id}/train")
async def train(dataset_id: str, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    try:
        out = train_all(d["path"], dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.datasets.update_one(
        {"_id": d["_id"]},
        {"$set": {
            "trained": True,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "model_results": out["results"],
            "best_model": out["best_model"],
            "feature_keys": out["feature_keys"],
        }},
    )
    return out


@api.get("/datasets/{dataset_id}/models")
async def get_models(dataset_id: str, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {
        "trained": bool(d.get("trained")),
        "results": d.get("model_results", []),
        "best_model": d.get("best_model"),
        "feature_keys": d.get("feature_keys", []),
    }


class PredictIn(BaseModel):
    dataset_id: str
    features: Dict[str, float]
    location: Optional[str] = None
    date: Optional[str] = None


@api.post("/predict")
async def predict(payload: PredictIn, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(payload.dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not d.get("trained"):
        raise HTTPException(status_code=400, detail="Dataset is not trained yet — please train models first.")
    try:
        pred = predict_from_model(payload.dataset_id, payload.features)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    aqi_info = classify_aqi(pred["prediction"])
    doc = {
        "user_id": ObjectId(user["id"]),
        "dataset_id": ObjectId(payload.dataset_id),
        "dataset_name": d["name"],
        "features": payload.features,
        "location": payload.location,
        "date": payload.date,
        "aqi": aqi_info["aqi"],
        "category": aqi_info["category"],
        "color": aqi_info["color"],
        "advice": aqi_info["advice"],
        "model": pred["model"],
        "confidence": round(max(0.0, min(100.0, 100.0 - float(pred.get("rmse", 0)))), 1),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.predictions.insert_one(doc)
    return {"id": str(result.inserted_id), **{k: v for k, v in doc.items() if k not in ("user_id", "dataset_id", "_id")}}


@api.get("/history")
async def history(user=Depends(get_current_user)):
    cursor = db.predictions.find({"user_id": ObjectId(user["id"])}).sort("created_at", -1).limit(200)
    items = []
    async for p in cursor:
        p = _serialize(p)
        p["dataset_id"] = str(p.pop("dataset_id"))
        p.pop("user_id", None)
        items.append(p)
    return items

@api.delete("/history/{prediction_id}")
async def delete_prediction(prediction_id: str, user=Depends(get_current_user)):
    result = await db.predictions.delete_one({"_id": _oid(prediction_id), "user_id": ObjectId(user["id"])})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"ok": True}


@api.post("/forecast/{dataset_id}")
async def forecast(dataset_id: str, days: int = 7, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not d.get("trained"):
        raise HTTPException(status_code=400, detail="Dataset is not trained yet.")
    fc = forecast_next_days(dataset_id, d["path"], days=min(max(days, 1), 14))
    for row in fc:
        info = classify_aqi(row["aqi"])
        row.update({"category": info["category"], "color": info["color"]})
    return fc


# ────────────────────────────────────────────────────────────────────────────
# AI INSIGHTS
# ────────────────────────────────────────────────────────────────────────────
@api.post("/datasets/{dataset_id}/insights")
async def insights(dataset_id: str, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = load_dataset_df(d["path"])
    df = ensure_aqi(df, d["schema"])
    summary = {
        "rows": int(len(df)),
        "avg_aqi": round(float(df["AQI"].mean()), 1),
        "max_aqi": round(float(df["AQI"].max()), 1),
        "min_aqi": round(float(df["AQI"].min()), 1),
        "pollutant_means": pollutant_comparison(df, d["schema"]),
        "aqi_distribution": aqi_distribution(df),
        "monthly_trend": monthly_trend(df, d["schema"].get("date"))[-12:],
    }
    try:
        text = await generate_insight(summary, session_id=f"insight_{dataset_id}")
    except Exception as e:
        logger.exception("insight generation failed")
        raise HTTPException(status_code=502, detail=f"Insight generation failed: {e}")
    return {"summary": summary, "insight": text}


# ────────────────────────────────────────────────────────────────────────────
# REPORTS
# ────────────────────────────────────────────────────────────────────────────
@api.get("/reports/prediction/{prediction_id}")
async def prediction_report(prediction_id: str, user=Depends(get_current_user)):
    p = await db.predictions.find_one({"_id": _oid(prediction_id), "user_id": ObjectId(user["id"])})
    if not p:
        raise HTTPException(status_code=404, detail="Prediction not found")
    pdf = build_prediction_pdf(
        {
            "aqi": p.get("aqi"),
            "category": p.get("category"),
            "advice": p.get("advice"),
            "model": p.get("model"),
            "location": p.get("location") or "—",
            "date": p.get("date") or "—",
            "inputs": p.get("features") or {},
        },
        user["email"],
    )
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="prediction_{prediction_id}.pdf"'},
    )


@api.get("/reports/model/{dataset_id}")
async def model_report(dataset_id: str, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d or not d.get("trained"):
        raise HTTPException(status_code=404, detail="No trained model found for this dataset")
    pdf = build_model_metrics_pdf(d["name"], d.get("model_results", []), d.get("best_model", "—"))
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="model_{dataset_id}.pdf"'},
    )


@api.get("/reports/dataset/{dataset_id}/csv")
async def dataset_csv(dataset_id: str, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    csv_bytes = Path(d["path"]).read_bytes()
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{d["name"]}"'},
    )


# ────────────────────────────────────────────────────────────────────────────
# CITY COMPARISON
# ────────────────────────────────────────────────────────────────────────────
@api.get("/datasets/{dataset_id}/compare")
async def compare_cities(dataset_id: str, city_a: str, city_b: str, user=Depends(get_current_user)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id), "user_id": ObjectId(user["id"])})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    loc_col = d["schema"].get("location")
    if not loc_col:
        raise HTTPException(status_code=400, detail="Dataset has no location column.")
    df = load_dataset_df(d["path"])
    df = ensure_aqi(df, d["schema"])

    def _agg(city: str) -> Dict:
        sub = df[df[loc_col].astype(str).str.lower() == city.lower()]
        if sub.empty:
            return {"city": city, "found": False}
        return {
            "city": city,
            "found": True,
            "avg_aqi": round(float(sub["AQI"].mean()), 1),
            "max_aqi": round(float(sub["AQI"].max()), 1),
            "min_aqi": round(float(sub["AQI"].min()), 1),
            "samples": int(len(sub)),
        }
    return {"a": _agg(city_a), "b": _agg(city_b)}


# ────────────────────────────────────────────────────────────────────────────
# ADMIN
# ────────────────────────────────────────────────────────────────────────────
@api.get("/admin/users")
async def admin_users(_admin=Depends(get_current_admin)):
    cursor = db.users.find({}).sort("created_at", -1)
    users = []
    async for u in cursor:
        users.append(_serialize(u))
    return users


@api.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin=Depends(get_current_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    result = await db.users.delete_one({"_id": _oid(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


@api.get("/admin/datasets")
async def admin_datasets(_admin=Depends(get_current_admin)):
    cursor = db.datasets.find({}).sort("created_at", -1)
    items = []
    async for d in cursor:
        d = _serialize(d)
        d["user_id"] = str(d.pop("user_id"))
        items.append(d)
    return items


@api.delete("/admin/datasets/{dataset_id}")
async def admin_delete_dataset(dataset_id: str, _admin=Depends(get_current_admin)):
    d = await db.datasets.find_one({"_id": _oid(dataset_id)})
    if not d:
        raise HTTPException(status_code=404, detail="Dataset not found")
    try:
        Path(d["path"]).unlink(missing_ok=True)
    except Exception:
        pass
    await db.datasets.delete_one({"_id": d["_id"]})
    return {"ok": True}


@api.get("/admin/analytics")
async def admin_analytics(_admin=Depends(get_current_admin)):
    users_total = await db.users.count_documents({})
    datasets_total = await db.datasets.count_documents({})
    predictions_total = await db.predictions.count_documents({})
    trained_total = await db.datasets.count_documents({"trained": True})

    # last 7 days predictions
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent = await db.predictions.count_documents({"created_at": {"$gte": cutoff}})

    # top locations
    pipeline = [
        {"$match": {"location": {"$ne": None}}},
        {"$group": {"_id": "$location", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    top_locations = [{"location": r["_id"], "count": r["count"]} async for r in db.predictions.aggregate(pipeline)]

    return {
        "users": users_total,
        "datasets": datasets_total,
        "predictions": predictions_total,
        "trained_models": trained_total,
        "recent_predictions_7d": recent,
        "top_locations": top_locations,
    }


@api.get("/admin/predictions")
async def admin_predictions(_admin=Depends(get_current_admin)):
    cursor = db.predictions.find({}).sort("created_at", -1).limit(200)
    items = []
    async for p in cursor:
        p = _serialize(p)
        p["dataset_id"] = str(p.pop("dataset_id"))
        p["user_id"] = str(p.pop("user_id"))
        items.append(p)
    return items


# ────────────────────────────────────────────────────────────────────────────
# HEALTH / ROOT
# ────────────────────────────────────────────────────────────────────────────
@api.get("/")
async def root():
    return {"service": "AeroPulse API", "status": "ok"}


@api.get("/aqi/categories")
async def aqi_categories():
    from aqi_utils import AQI_CATEGORIES
    return AQI_CATEGORIES


app.include_router(api)

# CORS — use explicit origins when we're using credentialed cookies
cors_env = os.environ.get("CORS_ORIGINS", "*")
frontend_url = os.environ.get("FRONTEND_URL", "").strip()
origins: List[str] = []
if cors_env and cors_env != "*":
    origins = [o.strip() for o in cors_env.split(",") if o.strip()]
if frontend_url and frontend_url not in origins:
    origins.append(frontend_url)
# Always add local dev
for dev in ("http://localhost:3000", "http://127.0.0.1:3000"):
    if dev not in origins:
        origins.append(dev)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")), reload=False)
