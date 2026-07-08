"""Authentication helpers — JWT, password hashing, dependencies."""
import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import HTTPException, Request

JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = 60 * 12  # 12 hours
REFRESH_TTL_DAYS = 7
# Default cookies to Secure on production HTTPS. Override to "false" for local http dev.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "lax").lower()


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN)
    return jwt.encode({"sub": user_id, "email": email, "exp": exp, "type": "access"}, _secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL_DAYS)
    return jwt.encode({"sub": user_id, "exp": exp, "type": "refresh"}, _secret(), algorithm=JWT_ALGORITHM)


def set_auth_cookies(response, access: str, refresh: str) -> None:
    response.set_cookie("access_token", access, httponly=True, secure=COOKIE_SECURE,
                        samesite=COOKIE_SAMESITE, max_age=ACCESS_TTL_MIN * 60, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=COOKIE_SECURE,
                        samesite=COOKIE_SAMESITE, max_age=REFRESH_TTL_DAYS * 86400, path="/")


def clear_auth_cookies(response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    return token


async def get_current_user(request: Request):
    from server import db  # local import to avoid circular
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        try:
            user_oid = ObjectId(payload["sub"])
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token subject")
        user = await db.users.find_one({"_id": user_oid})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["id"] = str(user["_id"])
        del user["_id"]
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_admin(request: Request):
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def seed_admin(db) -> None:
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@aqi.io")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    now = datetime.now(timezone.utc).isoformat()
    if existing is None:
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": "Administrator",
            "role": "admin",
            "created_at": now,
        })
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"_id": existing["_id"]},
            {"$set": {"password_hash": hash_password(admin_password), "role": "admin"}}
        )

    # Seed a shared "guest" user so the frontend can auto-login without an auth screen.
    guest_email = "guest@aqi.io"
    if await db.users.find_one({"email": guest_email}) is None:
        await db.users.insert_one({
            "email": guest_email,
            "password_hash": hash_password("guest-auto-login"),
            "name": "Guest",
            "role": "user",
            "created_at": now,
        })
