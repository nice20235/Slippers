from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from fastapi.responses import JSONResponse
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
import uvicorn
import os

from app.db.database import init_db, close_db
from app.api.endpoints import users, slippers, orders, categories
from app.auth.routes import auth_router
from dotenv import load_dotenv
load_dotenv()

# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    # Startup
    print("🚀 Starting Restaurant Order System...")
    await init_db()
    print("✅ Application started successfully!")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    await close_db()
    print("✅ Application shutdown complete!")

# Create FastAPI application
app = FastAPI(
    title="Restaurant Order System API",
    description="""
    A modern restaurant ordering system with JWT-based authentication.
    
    ## Authentication
    
    1. Register a new user: `POST /auth/register`
    2. Login with credentials: `POST /auth/login`
    3. Use the JWT token in Authorization header: `Bearer <token>`
    4. Refresh tokens when needed: `POST /auth/refresh`
    
    ## Features
    
    * **JWT-based authentication** with access and refresh tokens
    * **Role-based access** (User/Admin)
    * **Slipper management** with categories
    * **Order processing** system
    * **User management** (Admin only)
    
    ## Usage
    
    For all protected endpoints, include the Authorization header:
    ```
    Authorization: Bearer <your_jwt_token>
    ```
    """,
    version="1.0.0",
    contact={
        "name": "Restaurant Order System",
        "url": "https://example.com",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "JWT-based authentication system"
        },
        {
            "name": "Users",
            "description": "User management operations (Admin only)"
        },
        {
            "name": "Categories",
            "description": "Slipper category management"
        },
        {
            "name": "Slippers",
            "description": "Slipper item management"
        },
        {
            "name": "Orders",
            "description": "Order management operations"
        },
        {
            "name": "Root",
            "description": "Basic API information"
        }
    ]
)

# CORS middleware configuration
allowed = [o.strip() for o in settings.ALLOWED_ORIGINS.split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Simple global rate limiting middleware (IP-based)
_req_log = defaultdict(deque)
_exclude = {p.strip() for p in settings.RATE_LIMIT_EXCLUDE_PATHS.split(',') if p.strip()}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path in _exclude:
        return await call_next(request)

    # Identify client IP
    if settings.TRUST_PROXY:
        fwd = request.headers.get("x-forwarded-for")
        client_ip = fwd.split(',')[0].strip() if fwd else request.client.host
    else:
        client_ip = request.client.host

    now = time.time()
    window = settings.RATE_LIMIT_WINDOW_SEC
    limit = settings.RATE_LIMIT_REQUESTS
    dq = _req_log[client_ip]
    while dq and now - dq[0] > window:
        dq.popleft()
    if len(dq) >= limit:
        reset_in = int(max(0, window - (now - dq[0]))) if dq else window
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"},
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_in)
            }
        )
    dq.append(now)
    remaining = max(0, limit - len(dq))
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    # rough reset for the oldest item in window
    reset_in = int(max(0, window - (now - dq[0]))) if dq else window
    response.headers["X-RateLimit-Reset"] = str(reset_in)
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for better error responses"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if os.getenv("DEBUG", "False").lower() == "true" else "Something went wrong"
        }
    )

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(categories.router, prefix="/categories", tags=["Categories"])
app.include_router(slippers.router, prefix="/slippers", tags=["Slippers"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Restaurant Order System",
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 