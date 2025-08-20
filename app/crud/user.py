from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.auth.password import verify_password
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.orders))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()

async def get_user_by_name(db: AsyncSession, name: str) -> Optional[User]:
    """Get user by name"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.orders))
        .where(User.name == name)
    )
    return result.scalar_one_or_none()

async def get_user_by_phone_number(db: AsyncSession, phone_number: str) -> Optional[User]:
    """Get user by phone number"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.orders))
        .where(User.phone_number == phone_number)
    )
    return result.scalar_one_or_none()

async def authenticate_user(db: AsyncSession, name: str, password: str) -> Optional[User]:
    """Authenticate user by name and password"""
    user = await get_user_by_name(db, name)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

async def get_users(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    is_admin: Optional[bool] = None
) -> Tuple[List[User], int]:
    """Get users with pagination and filters"""
    # Build query
    query = select(User).options(selectinload(User.orders))
    
    # Apply filters
    if is_admin is not None:
        query = query.where(User.is_admin == is_admin)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    result = await db.execute(query.offset(skip).limit(limit))
    users = result.scalars().all()
    
    return users, total

async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """Create new user"""
    # Get user data without hashing password
    user_data = user.model_dump()
    password = user_data.pop('password')
    user_data.pop('confirm_password', None)  # Remove confirm_password as it's not stored
    
    # Store password directly (no hashing)
    user_data['password_hash'] = password
    
    db_user = User(**user_data)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # Load relationships
    result = await db.execute(
        select(User)
        .options(selectinload(User.orders))
        .where(User.id == db_user.id)
    )
    return result.scalar_one()

async def update_user(db: AsyncSession, db_user: User, user_update: UserUpdate) -> User:
    """Update user"""
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # Load relationships
    result = await db.execute(
        select(User)
        .options(selectinload(User.orders))
        .where(User.id == db_user.id)
    )
    return result.scalar_one()

async def delete_user(db: AsyncSession, db_user: User) -> bool:
    """Delete user"""
    await db.delete(db_user)
    await db.commit()
    return True

async def promote_to_admin(db: AsyncSession, name: str) -> Optional[User]:
    """Promote user to admin by name"""
    user = await get_user_by_name(db, name)
    if not user:
        return None
    
    user.is_admin = True
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Load relationships
    result = await db.execute(
        select(User)
        .options(selectinload(User.orders))
        .where(User.id == user.id)
    )
    return result.scalar_one()

async def update_user_password(db: AsyncSession, name: str, new_password: str) -> Optional[User]:
    """Update user password by name"""
    user = await get_user_by_name(db, name)
    if not user:
        return None
    
    # Store new password directly (no hashing as per your request)
    user.password_hash = new_password
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"Password updated for user: {user.name}")
    return user 