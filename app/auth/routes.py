from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.auth.jwt import create_access_token, create_refresh_token, decode_refresh_token
from app.crud.user import create_user, authenticate_user, get_user_by_name, get_user_by_phone_number, get_user
from app.schemas.user import UserCreate, UserLogin, TokenResponse, RefreshTokenRequest, UserResponse

import logging
import time
from collections import defaultdict, deque
from app.core.config import settings

logger = logging.getLogger(__name__)

auth_router = APIRouter()

# In-memory rate limit storage: key -> deque[timestamps]
_login_attempts = defaultdict(deque)

def _rate_limit_key(name: str, client_ip: str) -> str:
    return f"{client_ip}:{name}" if name else client_ip

def check_login_rate_limit(name: str, client_ip: str):
    now = time.time()
    window = settings.LOGIN_RATE_WINDOW_SEC
    limit = settings.LOGIN_RATE_LIMIT
    key = _rate_limit_key(name, client_ip)
    dq = _login_attempts[key]
    # drop old
    while dq and now - dq[0] > window:
        dq.popleft()
    if len(dq) >= limit:
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
    # record attempt
    dq.append(now)


@auth_router.post("/register")
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    response: Response = None
):
    # Check if user with same name already exists
    existing_user_by_name = await get_user_by_name(db, user_data.name)
    if existing_user_by_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this name already exists"
        )
    # Check if user with same phone number already exists
    existing_user_by_phone = await get_user_by_phone_number(db, user_data.phone_number)
    if existing_user_by_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this phone number already exists"
        )
    # Create new user
    user = await create_user(db, user_data)
    logger.info(f"Created new user: {user.name} ({user.phone_number})")
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    # Set tokens as HttpOnly cookies (config-driven)
    response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True,
        secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN
    )
    user_data = UserResponse.from_orm(user).dict()
    user_data.pop("id", None)
    return {"message": "User registered successfully", "user": user_data}


@auth_router.post("/login")
async def login_user(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
    response: Response = None,
    request: Request = None
):
    """
    Login user with name and password
    """
    # Rate-limit by user name + client IP
    client_ip = request.client.host if request and request.client else "unknown"
    check_login_rate_limit(user_credentials.name, client_ip)
    # Authenticate user
    user = await authenticate_user(db, user_credentials.name, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect name or password"
        )
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    # Set tokens as HttpOnly cookies (config-driven)
    response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True,
        secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN
    )
    logger.info(f"User logged in successfully: {user.name} (ID: {user.id})")
    user_data = UserResponse.from_orm(user).dict()
    user_data.pop("id", None)
    return {"message": "Login successful", "user": user_data}


@auth_router.post("/refresh")
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    response: Response = None
):
    """
    Refresh access token using refresh token
    """
    # Decode refresh token
    payload = decode_refresh_token(refresh_request.refresh_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    # Get user
    user_id = int(payload["sub"])
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    # Set tokens as HttpOnly cookies (config-driven)
    response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True,
        secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN
    )
    logger.info(f"Token refreshed for user: {user.name} (ID: {user.id})")
    user_data = UserResponse.from_orm(user).dict()
    user_data.pop("id", None)
    return {"message": "Token refreshed", "user": user_data}

@auth_router.post("/logout")
async def logout(response: Response):
    """
    Logout user by clearing auth cookies
    """
    response.delete_cookie(key="access_token", domain=settings.COOKIE_DOMAIN)
    response.delete_cookie(key="refresh_token", domain=settings.COOKIE_DOMAIN)
    return {"message": "Logged out successfully"}

