"""
Optimized response models with minimal data transfer
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class BaseResponse(BaseModel):
    """Base response model with optimized serialization"""
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        },
        # Optimize JSON serialization
        ser_json_timedelta='float',
        validate_assignment=True
    )

class MinimalSlipperResponse(BaseResponse):
    """Minimal slipper data for list views"""
    id: int
    name: str
    price: float
    image: Optional[str] = None
    quantity: int = Field(description="Available quantity")

class SlipperSummaryResponse(BaseResponse):
    """Summary slipper data with category info"""
    id: int
    name: str
    size: str
    price: float
    quantity: int
    category_name: Optional[str] = None
    image: Optional[str] = None
    is_available: bool = Field(default=True, description="Whether slipper is in stock")

class SlipperDetailResponse(BaseResponse):
    """Full slipper data for detail views"""
    id: int
    name: str
    size: str
    price: float
    quantity: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    image: Optional[str] = None
    images: List[Dict[str, Any]] = Field(default_factory=list, description="All slipper images")
    is_available: bool = Field(default=True)
    created_at: datetime
    updated_at: Optional[datetime] = None

class MinimalOrderResponse(BaseResponse):
    """Minimal order data for list views"""
    id: int
    status: str
    total_amount: float
    created_at: datetime

class OrderSummaryResponse(BaseResponse):
    """Order summary with user info"""
    id: int
    user_name: Optional[str] = None
    status: str
    total_amount: float
    delivery_address: Optional[str] = None
    created_at: datetime

class MinimalUserResponse(BaseResponse):
    """Minimal user data for admin lists"""
    id: int
    name: str
    login: str
    is_admin: bool = False
    is_active: bool = True

class ApiResponse(BaseResponse):
    """Standard API response wrapper"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[List[str]] = None

class PaginationMeta(BaseResponse):
    """Pagination metadata"""
    page: int
    size: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool

class OptimizedPaginatedResponse(BaseResponse):
    """Optimized paginated response with minimal metadata"""
    items: List[Any]
    meta: PaginationMeta
    
    @classmethod
    def create(
        cls,
        items: List[Any],
        total: int,
        page: int,
        size: int
    ):
        """Create optimized paginated response"""
        pages = (total + size - 1) // size
        meta = PaginationMeta(
            page=page,
            size=size,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )
        return cls(items=items, meta=meta)

class HealthCheckResponse(BaseResponse):
    """Health check response"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    database: bool = True
    cache: bool = True

class ErrorResponse(BaseResponse):
    """Standardized error response"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
