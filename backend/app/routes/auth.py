"""
Authentication Endpoints & JWT Token Management.
"""

import base64
import json
import hmac
from datetime import datetime, timedelta
import hashlib
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

try:
    from jose import JWTError, jwt
    HAS_JOSE = True
except ImportError:
    HAS_JOSE = False

from backend.app.config import settings
from backend.app.db.models import User
from backend.app.db.mongo import get_collection

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: Optional[str] = "teacher"


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = "optiscan_salt_2026"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": int(expire.timestamp())})

    if HAS_JOSE:
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    # Lightweight HMAC Fallback Token
    payload_b64 = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode()
    sig = hmac.new(settings.SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    email = None

    if HAS_JOSE:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email = payload.get("sub")
        except Exception:
            raise credentials_exception
    else:
        try:
            parts = token.split(".")
            if len(parts) != 2:
                raise credentials_exception
            payload_b64, sig = parts
            expected_sig = hmac.new(settings.SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                raise credentials_exception
            payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())
            email = payload.get("sub")
        except Exception:
            raise credentials_exception

    if email is None:
        raise credentials_exception

    users_col = get_collection("users")
    user_doc = await users_col.find_one({"email": email})
    if user_doc is None:
        # Return fallback demo user if matching
        if email == "teacher@optiscan.dev":
            return User(
                _id="demo-teacher-id",
                email="teacher@optiscan.dev",
                full_name="Demo Educator",
                hashed_password=hash_password("optiscan2026"),
                role="teacher",
            )
        raise credentials_exception

    return User(**user_doc)


@router.post("/register", response_model=Token)
async def register(user_in: UserCreate):
    users_col = get_collection("users")
    existing = await users_col.find_one({"email": user_in.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    user_dict = {
        "_id": str(uuid.uuid4()),
        "email": user_in.email,
        "full_name": user_in.full_name,
        "hashed_password": hash_password(user_in.password),
        "role": user_in.role or "teacher",
        "created_at": datetime.utcnow(),
    }
    await users_col.insert_one(user_dict)

    token = create_access_token({"sub": user_in.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_dict["_id"],
            "email": user_dict["email"],
            "full_name": user_dict["full_name"],
            "role": user_dict["role"],
        },
    }


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    users_col = get_collection("users")
    user_doc = await users_col.find_one({"email": form_data.username})

    # Default demo teacher if no users exist
    if not user_doc and form_data.username == "teacher@optiscan.dev":
        user_doc = {
            "_id": "demo-teacher-id",
            "email": "teacher@optiscan.dev",
            "full_name": "Demo Educator",
            "hashed_password": hash_password("optiscan2026"),
            "role": "teacher",
            "created_at": datetime.utcnow(),
        }
        await users_col.insert_one(user_doc)

    if not user_doc or not verify_password(form_data.password, user_doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user_doc["email"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_doc.get("_id"),
            "email": user_doc["email"],
            "full_name": user_doc["full_name"],
            "role": user_doc.get("role", "teacher"),
        },
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
    }
