"""AeroPulse automated AQI prediction backend."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import io
import logging
import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from auth import (
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    seed_admin,
    set_auth_cookies,
    verify_password,
)
from forecast_service import forecast_next_7_days
from location_service import geocode_location, reverse_geocode
from model_loader_service import load_production_model, model_status
from reports_service import build_prediction_pdf
from services.data_collector import collect_historical_data
from services.training_service import dataset_statistics, feature_importance, latest_model_metrics, run_full_training_pipeline, train_production_model, training_history, training_report, training_status
from waqi_service import fetch_waqi_environment
from weather_service import fetch_environment

mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
db = client[os.environ.get("DB_NAME", "aeropulse")]

logger = logging.getLogger("aeropulse")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

app = FastAPI(title="AeroPulse API", version="2.0.0")
api = APIRouter(prefix="/api")
_retraining_task = None


async def _weekly_retraining_loop():
    interval_seconds = int(os.environ.get("RETRAIN_INTERVAL_SECONDS", str(7 * 24 * 60 * 60)))
    collect_days = int(os.environ.get("RETRAIN_COLLECT_DAYS", "30"))
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            logger.info("Scheduled ML refresh started.")
            await collect_historical_data(db, days=collect_days)
            await train_production_model(db, replace_only_if_better=True)
            logger.info("Scheduled ML refresh completed.")
        except Exception:
            logger.exception("Scheduled ML refresh failed.")


@app.on_event("startup")
async def _startup():
    global _retraining_task
    await db.users.create_index("email", unique=True)
    await db.predictions.create_index("user_id")
    await db.login_attempts.create_index("identifier")
    await seed_admin(db)
    loaded_model = load_production_model()
    if os.environ.get("DISABLE_SCHEDULED_RETRAINING", "false").lower() not in {"1", "true", "yes"}:
        _retraining_task = asyncio.create_task(_weekly_retraining_loop())
    logger.info("Startup complete; production model loaded=%s.", bool(loaded_model))


@app.on_event("shutdown")
async def _shutdown():
    if _retraining_task:
        _retraining_task.cancel()
    client.close()


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


def _serialize(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    for key, value in list(doc.items()):
        if isinstance(value, ObjectId):
            doc[key] = str(value)
    doc.pop("password_hash", None)
    return doc


def _openweather_key() -> str:
    key = os.environ.get("OPENWEATHER_API_KEY") or os.environ.get("REACT_APP_OPENWEATHER_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="OPENWEATHER_API_KEY is not configured on the backend.")
    return key


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1, max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class PasswordIn(BaseModel):
    password: str = Field(min_length=6)


class LocationPredictIn(BaseModel):
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CollectDataIn(BaseModel):
    days: int = Field(default=90, ge=7, le=730)


def _require_admin(user: Dict[str, Any]):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@api.post("/auth/register")
async def register(payload: RegisterIn, response: Response):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
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
    return _serialize(await db.users.find_one({"_id": result.inserted_id}))


@api.post("/auth/login")
async def login(payload: LoginIn, request: Request, response: Response):
    email = payload.email.lower()
    attempts = await db.login_attempts.find_one({"identifier": email})
    if attempts and attempts.get("count", 0) >= 5:
        locked_at = attempts.get("locked_at")
        if locked_at and (datetime.now(timezone.utc).timestamp() - locked_at) < 900:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        await db.login_attempts.update_one(
            {"identifier": email},
            {"$inc": {"count": 1}, "$set": {"locked_at": datetime.now(timezone.utc).timestamp()}},
            upsert=True,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await db.login_attempts.delete_one({"identifier": email})
    uid = str(user["_id"])
    set_auth_cookies(response, create_access_token(uid, email), create_refresh_token(uid))
    return _serialize(user)


@api.post("/auth/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


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
    await db.predictions.delete_many({"user_id": uid})
    await db.users.delete_one({"_id": uid})
    clear_auth_cookies(response)
    return {"ok": True}


@api.get("/model/production")
async def production_model_info(user=Depends(get_current_user)):
    return model_status()


@api.post("/predict/location")
async def predict_location(payload: LocationPredictIn, user=Depends(get_current_user)):
    api_key = _openweather_key()
    try:
        if payload.latitude is not None and payload.longitude is not None:
            location_info = await reverse_geocode(api_key, payload.latitude, payload.longitude)
        elif payload.country and payload.city:
            location_info = await geocode_location(api_key, payload.country, payload.city, payload.state)
        else:
            raise HTTPException(status_code=400, detail="Provide country and city, or latitude and longitude.")
        try:
            environment = await fetch_waqi_environment(
                city=location_info.get("city") or payload.city or location_info.get("name"),
                latitude=location_info["latitude"],
                longitude=location_info["longitude"],
            )
            logger.info("Using WAQI")
            try:
                openweather_environment = await fetch_environment(api_key, location_info["latitude"], location_info["longitude"])
                environment["weather_forecast"] = openweather_environment.get("weather_forecast", [])
                for key in ("sunrise", "sunset", "weather_condition", "timezone"):
                    if environment.get(key) is None:
                        environment[key] = openweather_environment.get(key)
                for key in ("temp", "humidity", "pressure", "wind", "visibility"):
                    if environment["measurements"].get(key) is None:
                        environment["measurements"][key] = openweather_environment.get("measurements", {}).get(key)
            except Exception as forecast_exc:
                logger.warning("WAQI succeeded; OpenWeather forecast enrichment failed: %s", forecast_exc)
        except Exception as waqi_exc:
            logger.warning("Using OpenWeather fallback: %s", waqi_exc)
            environment = await fetch_environment(api_key, location_info["latitude"], location_info["longitude"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("OpenWeather lookup failed")
        raise HTTPException(status_code=502, detail=f"Unable to fetch live environmental data: {exc}")

    features = {key: value for key, value in environment["measurements"].items() if value is not None}
    model_info = model_status()
    metrics = model_info.get("metrics") or {}
    forecast = forecast_next_7_days(environment["measurements"], environment.get("weather_forecast"))
    tomorrow = forecast[0] if forecast else None

    official_aqi = environment.get("official_aqi")
    comparison = None
    if official_aqi is not None and tomorrow:
        difference = round(float(tomorrow["predicted_aqi"]) - float(official_aqi), 1)
        comparison = {
            "official_aqi": official_aqi,
            "tomorrow_predicted_aqi": tomorrow["predicted_aqi"],
            "difference": difference,
            "note": f"Compares today's {environment.get('source', 'live')} AQI with tomorrow's model forecast. Values may use different scales and are informational only.",
        }

    model_performance = {
        "algorithm": model_info.get("model_name"),
        "training_accuracy": round(max(0.0, float(metrics.get("r2", 0.0))) * 100, 1) if metrics else None,
        "rmse": metrics.get("rmse"),
        "mae": metrics.get("mae"),
        "r2_score": metrics.get("r2"),
        "mape": metrics.get("mape"),
        "model_version": model_info.get("model_version"),
        "training_date": model_info.get("trained_at"),
        "dataset_size": model_info.get("dataset_rows"),
        "feature_importance": model_info.get("feature_importance", []),
    }
    doc = {
        "user_id": ObjectId(user["id"]),
        "features": features,
        "location": location_info["name"],
        "date": datetime.now(timezone.utc).date().isoformat(),
        "aqi": tomorrow.get("predicted_aqi") if tomorrow else None,
        "predicted_aqi": tomorrow.get("predicted_aqi") if tomorrow else None,
        "category": tomorrow.get("category") if tomorrow else None,
        "color": tomorrow.get("color") if tomorrow else None,
        "advice": tomorrow.get("health_advice") if tomorrow else None,
        "health_advice": tomorrow.get("health_advice") if tomorrow else None,
        "risk_level": tomorrow.get("risk") if tomorrow else None,
        "explanation": tomorrow.get("explanation") if tomorrow else None,
        "model": model_info.get("model_name"),
        "confidence": tomorrow.get("confidence") if tomorrow else None,
        "ai_forecast": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_name": model_info.get("model_name"),
            "model_version": model_info.get("model_version"),
            "days": forecast,
        },
        "live_data": {"location": location_info, **environment},
        "model_performance": model_performance,
        "official_comparison": comparison,
        "forecast": forecast,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.predictions.insert_one(doc)
    return {"id": str(result.inserted_id), **{key: value for key, value in doc.items() if key not in ("user_id", "_id")}}


@api.get("/forecast/latest")
async def latest_forecast(user=Depends(get_current_user)):
    prediction = await db.predictions.find_one({"user_id": ObjectId(user["id"]), "forecast": {"$exists": True}}, sort=[("created_at", -1)])
    if not prediction:
        return {"forecast": [], "location": None, "created_at": None}
    return {
        "forecast": prediction.get("forecast", []),
        "location": prediction.get("location"),
        "created_at": prediction.get("created_at"),
        "prediction_id": str(prediction["_id"]),
    }


@api.get("/history")
async def history(user=Depends(get_current_user)):
    cursor = db.predictions.find({"user_id": ObjectId(user["id"])}).sort("created_at", -1).limit(200)
    items = []
    async for prediction in cursor:
        prediction = _serialize(prediction)
        prediction.pop("user_id", None)
        items.append(prediction)
    return items


@api.delete("/history/{prediction_id}")
async def delete_prediction(prediction_id: str, user=Depends(get_current_user)):
    result = await db.predictions.delete_one({"_id": _oid(prediction_id), "user_id": ObjectId(user["id"])})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"ok": True}


@api.get("/reports/prediction/{prediction_id}")
async def prediction_report(prediction_id: str, user=Depends(get_current_user)):
    prediction = await db.predictions.find_one({"_id": _oid(prediction_id), "user_id": ObjectId(user["id"])})
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    pdf = build_prediction_pdf(
        {
            "aqi": prediction.get("aqi"),
            "category": prediction.get("category"),
            "advice": prediction.get("advice"),
            "model": prediction.get("model"),
            "location": prediction.get("location") or "-",
            "date": prediction.get("date") or "-",
            "inputs": prediction.get("features") or {},
            "current_conditions": (prediction.get("live_data") or {}).get("measurements") or {},
            "forecast": prediction.get("forecast") or [],
            "model_metrics": prediction.get("model_performance") or {},
            "feature_importance": ((prediction.get("forecast") or [{}])[0] or {}).get("feature_importance", []),
            "weather_summary": [
                {
                    "label": item.get("label"),
                    "summary": item.get("weather_summary"),
                    "temp": (item.get("weather") or {}).get("temp"),
                    "wind": (item.get("weather") or {}).get("wind"),
                    "rain": (item.get("weather") or {}).get("rain"),
                }
                for item in (prediction.get("forecast") or [])
            ],
        },
        user["email"],
    )
    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="prediction_{prediction_id}.pdf"'},
    )


@api.get("/admin/analytics")
async def admin_analytics(user=Depends(get_current_user)):
    _require_admin(user)
    users_total = await db.users.count_documents({})
    predictions_total = await db.predictions.count_documents({})
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent = await db.predictions.count_documents({"created_at": {"$gte": cutoff}})
    pipeline = [
        {"$match": {"location": {"$ne": None}}},
        {"$group": {"_id": "$location", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    top_locations = [{"location": row["_id"], "count": row["count"]} async for row in db.predictions.aggregate(pipeline)]
    return {
        "users": users_total,
        "predictions": predictions_total,
        "recent_predictions_7d": recent,
        "top_locations": top_locations,
    }


@api.post("/admin/collect-data")
async def admin_collect_data(payload: CollectDataIn, user=Depends(get_current_user)):
    _require_admin(user)
    try:
        return await collect_historical_data(db, days=payload.days)
    except Exception as exc:
        logger.exception("Automated data collection failed")
        await db.training_logs.insert_one({
            "type": "collection",
            "status": "failed",
            "error": str(exc),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        raise HTTPException(status_code=500, detail=f"Data collection failed: {exc}")


@api.post("/admin/train-model")
async def admin_train_model(user=Depends(get_current_user)):
    _require_admin(user)
    try:
        return await train_production_model(db)
    except Exception as exc:
        logger.exception("Automated model training failed")
        await db.training_logs.insert_one({
            "type": "training",
            "status": "failed",
            "error": str(exc),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        raise HTTPException(status_code=500, detail=f"Model training failed: {exc}")


@api.post("/admin/retrain-pipeline")
async def admin_retrain_pipeline(payload: CollectDataIn, user=Depends(get_current_user)):
    _require_admin(user)
    try:
        return await run_full_training_pipeline(db, days=payload.days)
    except Exception as exc:
        logger.exception("Full ML pipeline failed")
        await db.training_logs.insert_one({
            "type": "full_pipeline",
            "status": "failed",
            "error": str(exc),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        raise HTTPException(status_code=500, detail=f"Full ML pipeline failed: {exc}")


@api.get("/admin/model-metrics")
async def admin_model_metrics(user=Depends(get_current_user)):
    _require_admin(user)
    return await latest_model_metrics(db)


@api.get("/admin/training-history")
async def admin_training_history(user=Depends(get_current_user)):
    _require_admin(user)
    return await training_history(db)


@api.get("/admin/training-status")
async def admin_training_status(user=Depends(get_current_user)):
    _require_admin(user)
    return await training_status(db)


@api.get("/admin/dataset-statistics")
async def admin_dataset_statistics(user=Depends(get_current_user)):
    _require_admin(user)
    return await dataset_statistics(db)


@api.get("/admin/feature-importance")
async def admin_feature_importance(user=Depends(get_current_user)):
    _require_admin(user)
    return await feature_importance(db)


@api.get("/admin/training-report")
async def admin_training_report(user=Depends(get_current_user)):
    _require_admin(user)
    return await training_report(db)


@api.get("/admin/model-versions")
async def admin_model_versions(user=Depends(get_current_user)):
    _require_admin(user)
    rows = []
    cursor = db.model_versions.find({}).sort("training_date", -1).limit(50)
    async for row in cursor:
        row = _serialize(row)
        rows.append(row)
    return rows


@api.get("/admin/predictions")
async def admin_predictions(user=Depends(get_current_user)):
    _require_admin(user)
    cursor = db.predictions.find({}).sort("created_at", -1).limit(200)
    items = []
    async for prediction in cursor:
        prediction = _serialize(prediction)
        prediction.pop("user_id", None)
        items.append(prediction)
    return items


@api.get("/")
async def root():
    return {"service": "AeroPulse API", "status": "ok"}


@api.get("/aqi/categories")
async def aqi_categories():
    from aqi_utils import AQI_CATEGORIES
    return AQI_CATEGORIES


app.include_router(api)

cors_env = os.environ.get("CORS_ORIGINS", "*")
frontend_url = os.environ.get("FRONTEND_URL", "").strip()
origins: List[str] = []
if cors_env and cors_env != "*":
    origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
if frontend_url and frontend_url not in origins:
    origins.append(frontend_url)
for dev_origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
    if dev_origin not in origins:
        origins.append(dev_origin)

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
