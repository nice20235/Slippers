from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    name: str = Field(
        ..., 
        description="User's first name", 
        min_length=2, 
        max_length=100,
        example="John"
    )
    surname: str = Field(
        ..., 
        description="User's last name", 
        min_length=2, 
        max_length=100,
        example="Doe"
    )
    phone_number: str = Field(
        ..., 
        description="User's phone number", 
        min_length=10, 
        max_length=20,
        example="+79991234567"
    )
    is_admin: bool = Field(
        default=False, 
        description="Whether user is an admin",
        example=False
    )

class UserCreate(UserBase):
    password: str = Field(
        ..., 
        description="User's password", 
        min_length=8,
        example="securepassword123"
    )
    confirm_password: str = Field(
        ..., 
        description="Confirm password", 
        example="securepassword123"
    )
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if not v.startswith('+'):
            raise ValueError('Phone number must start with +')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John",
                "surname": "Doe",
                "phone_number": "+79991234567",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
                "is_admin": False
            }
        }

class UserUpdate(BaseModel):
    name: Optional[str] = Field(
        None, 
        description="User's first name", 
        min_length=2, 
        max_length=100,
        example="John"
    )
    surname: Optional[str] = Field(
        None, 
        description="User's last name", 
        min_length=2, 
        max_length=100,
        example="Doe"
    )
    phone_number: Optional[str] = Field(
        None, 
        description="User's phone number", 
        min_length=10, 
        max_length=20,
        example="+79991234567"
    )
    is_admin: Optional[bool] = Field(
        None, 
        description="Whether user is an admin",
        example=False
    )
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if v is not None and not v.startswith('+'):
            raise ValueError('Phone number must start with +')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John",
                "surname": "Doe",
                "phone_number": "+79991234567",
                "is_admin": False
            }
        }

class UserInDB(UserBase):
    id: int = Field(..., description="User ID", example=1)
    created_at: datetime = Field(..., description="Account creation timestamp", example="2024-01-15T10:30:00Z")
    updated_at: datetime = Field(..., description="Last update timestamp", example="2024-01-15T10:30:00Z")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserResponse(UserInDB):
    """User response schema for API endpoints"""
    pass

class UserList(BaseModel):
    """Schema for list of users"""
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    skip: int = Field(..., description="Number of users skipped")
    limit: int = Field(..., description="Maximum number of users returned")

class UserLogin(BaseModel):
    name: str = Field(
        ..., 
        description="User's first name", 
        example="John"
    )
    password: str = Field(
        ..., 
        description="User's password", 
        example="securepassword123"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John",
                "password": "securepassword123"
            }
        }

class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in minutes")
    user: UserResponse = Field(..., description="User information")

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="JWT refresh token") 