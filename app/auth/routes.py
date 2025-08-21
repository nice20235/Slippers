from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.auth.jwt import create_access_token, create_refresh_token, decode_refresh_token
from app.crud.user import create_user, authenticate_user, get_user_by_name, get_user_by_phone_number, get_user, update_user_password
from app.schemas.user import UserCreate, UserLogin, RefreshTokenRequest, UserResponse, ForgotPasswordRequest

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
    # Return tokens via response headers
    if response is not None:
        response.headers["Authorization"] = f"Bearer {access_token}"
        response.headers["Refresh-Token"] = refresh_token
        response.headers["Token-Type"] = "bearer"
        response.headers["X-Expires-In"] = str(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_payload = UserResponse.from_orm(user).dict()
    user_payload.pop("id", None)
    return {"message": "User registered successfully", "user": user_payload}


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
    # Return tokens via response headers
    if response is not None:
        response.headers["Authorization"] = f"Bearer {access_token}"
        response.headers["Refresh-Token"] = refresh_token
        response.headers["Token-Type"] = "bearer"
        response.headers["X-Expires-In"] = str(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    logger.info(f"User logged in successfully: {user.name} (ID: {user.id})")
    user_payload = UserResponse.from_orm(user).dict()
    user_payload.pop("id", None)
    return {"message": "Login successful", "user": user_payload}


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
    # Return tokens via response headers
    if response is not None:
        response.headers["Authorization"] = f"Bearer {access_token}"
        response.headers["Refresh-Token"] = refresh_token
        response.headers["Token-Type"] = "bearer"
        response.headers["X-Expires-In"] = str(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    logger.info(f"Token refreshed for user: {user.name} (ID: {user.id})")
    user_payload = UserResponse.from_orm(user).dict()
    user_payload.pop("id", None)
    return {"message": "Token refreshed", "user": user_payload}

@auth_router.post("/logout")
async def logout():
    """
    Logout endpoint (no cookies to clear). Client should discard tokens stored on the frontend.
    """
    return {"message": "Logged out successfully"}


@auth_router.post("/forgot-password")
async def forgot_password(
    forgot_data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset user password by username
    """
    # Check if user exists
    user = await get_user_by_name(db, forgot_data.name)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this name not found"
        )
    
    # Update password
    updated_user = await update_user_password(db, forgot_data.name, forgot_data.new_password)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password"
        )
    
    logger.info(f"Password reset for user: {updated_user.name}")
    return {
        "message": "Password updated successfully",
        "user": {
            "name": updated_user.name,
            "surname": updated_user.surname,
            "phone_number": updated_user.phone_number,
            "is_admin": updated_user.is_admin
        }
    }

