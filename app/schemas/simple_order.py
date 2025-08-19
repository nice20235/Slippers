from pydantic import BaseModel, Field
from typing import Optional

class SimpleOrderCreate(BaseModel):
    """Simplified order creation schema"""
    slipper_id: int = Field(
        ..., 
        description="ID of the slipper to order",
        example=1,
        gt=0
    )
    quantity: int = Field(
        ..., 
        description="Quantity to order",
        example=2,
        gt=0,
        le=100
    )
    notes: Optional[str] = Field(
        None,
        description="Special instructions for the order",
        example="Extra cheese, no onions",
        max_length=500
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "slipper_id": 1,
                "quantity": 2,
                "notes": "Extra cheese, no onions"
            }
        }
