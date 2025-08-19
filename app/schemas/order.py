from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.order import OrderStatus

# Order Item schemas
class OrderItemBase(BaseModel):
    slipper_id: int = Field(
        ..., 
        description="Slipper ID", 
        gt=0,
        example=1
    )
    quantity: int = Field(
        ..., 
        description="Quantity ordered", 
        gt=0, 
        le=100,
        example=2
    )
    unit_price: float = Field(
        ..., 
        description="Unit price", 
        gt=0,
        example=650.0
    )
    notes: Optional[str] = Field(
        None, 
        description="Special instructions", 
        max_length=255,
        example="Extra cheese, please"
    )

class OrderItemCreate(OrderItemBase):
    class Config:
        json_schema_extra = {
            "example": {
                "slipper_id": 1,
                "quantity": 2,
                "unit_price": 650.0,
                "notes": "Extra cheese, please"
            }
        }

class OrderItemUpdate(BaseModel):
    quantity: Optional[int] = Field(
        None, 
        description="Quantity ordered", 
        gt=0, 
        le=100,
        example=2
    )
    unit_price: Optional[float] = Field(
        None, 
        description="Unit price", 
        gt=0,
        example=650.0
    )
    notes: Optional[str] = Field(
        None, 
        description="Special instructions", 
        max_length=255,
        example="Extra cheese, please"
    )

class OrderItemInDB(OrderItemBase):
    id: int = Field(..., description="Order item ID", example=1)
    order_id: int = Field(..., description="Order ID", example=1)
    total_price: float = Field(..., description="Total price for this item", example=1300.0)
    created_at: datetime = Field(..., description="Item creation timestamp", example="2024-01-15T10:30:00Z")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class OrderItemResponse(OrderItemInDB):
    """Order item response schema for API endpoints"""
    pass

# Order schemas
class OrderBase(BaseModel):
    user_id: int = Field(..., description="User ID", gt=0)
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Order status")
    total_amount: float = Field(default=0.0, description="Total order amount", ge=0)
    notes: Optional[str] = Field(None, description="Order notes", max_length=500)

class OrderCreate(BaseModel):
    user_id: int = Field(..., description="User ID", gt=0)
    items: List[OrderItemCreate] = Field(..., description="Order items", min_items=1)
    notes: Optional[str] = Field(None, description="Order notes", max_length=500)
    
    @validator('items')
    def validate_items(cls, v):
        if not v:
            raise ValueError('Order must have at least one item')
        return v

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = Field(None, description="Order status")
    total_amount: Optional[float] = Field(None, description="Total order amount", ge=0)
    notes: Optional[str] = Field(None, description="Order notes", max_length=500)

class OrderInDB(OrderBase):
    id: int = Field(..., description="Order ID")
    created_at: datetime = Field(..., description="Order creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    items: List[OrderItemInDB] = Field(..., description="Order items")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class OrderResponse(OrderInDB):
    """Order response schema for API endpoints"""
    pass

class OrderList(BaseModel):
    """Schema for list of orders"""
    orders: List[OrderResponse] = Field(..., description="List of orders")
    total: int = Field(..., description="Total number of orders")
    skip: int = Field(..., description="Number of orders skipped")
    limit: int = Field(..., description="Maximum number of orders returned")

# Status update schema
class OrderStatusUpdate(BaseModel):
    status: OrderStatus = Field(..., description="New order status")
    notes: Optional[str] = Field(None, description="Status update notes", max_length=500) 