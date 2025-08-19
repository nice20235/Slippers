from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Category schemas
class CategoryBase(BaseModel):
    name: str = Field(
        ..., 
        description="Category name", 
        min_length=1, 
        max_length=100,
        example="Men"
    )
    description: Optional[str] = Field(
        None, 
        description="Category description", 
        max_length=255,
        example="Men's slippers"
    )
    is_active: bool = Field(
        default=True, 
        description="Whether category is active",
        example=True
    )

class CategoryCreate(CategoryBase):
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Men",
                "description": "Men's slippers",
                "is_active": True
            }
        }

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(
        None, 
        description="Category name", 
        min_length=1, 
        max_length=100,
        example="Men"
    )
    description: Optional[str] = Field(
        None, 
        description="Category description", 
        max_length=255,
        example="Men's slippers"
    )
    is_active: Optional[bool] = Field(
        None, 
        description="Whether category is active",
        example=True
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Men",
                "description": "Men's slippers",
                "is_active": True
            }
        }

class CategoryInDB(CategoryBase):
    id: int = Field(..., description="Category ID", example=1)
    created_at: datetime = Field(..., description="Category creation timestamp", example="2024-01-15T10:30:00Z")
    updated_at: datetime = Field(..., description="Last update timestamp", example="2024-01-15T10:30:00Z")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CategoryResponse(CategoryInDB):
    """Category response schema for API endpoints"""
    pass

"""Deprecated food schemas kept temporarily to avoid breaking imports. Use app.schemas.slipper instead."""
class FoodBase(BaseModel):
    name: str = Field(..., description="Deprecated", example="Use Slipper schemas")
    description: Optional[str] = Field(None, description="Deprecated")
    price: float = Field(..., description="Deprecated")
    available: bool = Field(default=True, description="Deprecated")
    category_id: Optional[int] = Field(None, description="Deprecated")

class FoodCreate(FoodBase):
    pass

class FoodUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Deprecated")
    description: Optional[str] = Field(None, description="Deprecated")
    price: Optional[float] = Field(None, description="Deprecated")
    available: Optional[bool] = Field(None, description="Deprecated")
    category_id: Optional[int] = Field(None, description="Deprecated")

class FoodInDB(FoodBase):
    id: int = Field(..., description="Deprecated")
    created_at: datetime = Field(..., description="Deprecated")
    updated_at: datetime = Field(..., description="Deprecated")
    category: Optional[CategoryInDB] = Field(None, description="Deprecated")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FoodResponse(FoodInDB):
    pass

class FoodList(BaseModel):
    foods: List[FoodResponse] = Field(..., description="Deprecated")
    total: int = Field(..., description="Deprecated")
    skip: int = Field(..., description="Deprecated")
    limit: int = Field(..., description="Deprecated") 