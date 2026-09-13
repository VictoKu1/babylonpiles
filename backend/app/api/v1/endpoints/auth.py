"""JSON authentication and server-side role enforcement."""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.passwords import hash_password, verify_password
from app.models.user import User

router = APIRouter()
SESSION_COOKIE = "babylonpiles_session"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=1024)


class RegistrationRequest(LoginRequest):
    password: str = Field(min_length=12, max_length=1024)
    email: Optional[str] = Field(default=None, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=100)


def check_origin(request: Request, *, required: bool = True):
    """Cookie-authenticated mutations must originate from this deployment."""
    origin = request.headers.get("origin")
    expected = settings.public_origin or f"{request.url.scheme}://{request.headers.get('host', '')}"
    if origin is None and not required:
        return
    if not origin or origin.lower() != expected.rstrip("/").lower():
        raise HTTPException(status_code=403, detail="Request origin is not allowed")


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    claims = data.copy()
    claims["exp"] = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    claims["iat"] = datetime.utcnow()
    return jwt.encode(claims, settings.secret_key, algorithm="HS256")


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    authorization = request.headers.get("authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="Invalid authorization")
    else:
        token = request.cookies.get(SESSION_COOKIE)
        if token and request.method not in {"GET", "HEAD", "OPTIONS"}:
            check_origin(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"], options={"require_exp": True, "require_sub": True})
        user_id = int(claims["sub"])
    except (JWTError, ValueError, TypeError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    check_origin(request, required=False)
    user = (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
    if not user or not user.is_active or not await asyncio.to_thread(verify_password, body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict", path="/api",
                        secure=settings.cookie_secure or request.url.scheme == "https",
                        max_age=settings.access_token_expire_minutes * 60)
    response.headers["Cache-Control"] = "no-store"
    return {"success": True, "data": {"access_token": token, "token_type": "bearer", "user": user.to_dict()}}


@router.get("/me")
async def current_user(response: Response, user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return {"success": True, "data": user.to_dict()}


@router.post("/logout")
async def logout(request: Request, response: Response):
    if request.cookies.get(SESSION_COOKIE):
        check_origin(request)
    response.delete_cookie(SESSION_COOKIE, path="/api", httponly=True, samesite="strict")
    return {"success": True, "message": "Logged out"}


@router.post("/register", dependencies=[Depends(require_admin)])
async def register(body: RegistrationRequest, db: AsyncSession = Depends(get_db)):
    user = User(username=body.username, hashed_password=await asyncio.to_thread(hash_password, body.password),
                email=body.email, full_name=body.full_name, role="user", is_active=True)
    db.add(user)
    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username or email already exists")
    return {"success": True, "data": user.to_dict(), "message": "User registered"}
