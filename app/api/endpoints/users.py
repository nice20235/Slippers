from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.user import UserInDB, UserUpdate
from app.crud.user import get_users, get_user, delete_user, update_user
from app.auth.dependencies import get_current_admin

import logging

# Set up logging
logger = logging.getLogger(__name__)


router = APIRouter()

@router.get("/")
async def list_users(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    """
    List all users. Admin-only endpoint.
    """
    logger.info(f"Admin {admin.name} listing all users")
    users, total = await get_users(db)
    # Скрываем id и метаданные
    users_data = []
    for user in users:
        u = user.__dict__.copy()
        u.pop("id", None)
        u.pop("created_at", None)
        u.pop("updated_at", None)
        users_data.append(u)
    return users_data

@router.get("/{user_id}")
async def get_user_detail(user_id: int, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    """
    Get user details by ID. Admin-only endpoint.
    """
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"Admin {admin.name} viewing user details: {user.name} ({user.phone_number})")
    u = user.__dict__.copy()
    u.pop("id", None)
    u.pop("created_at", None)
    u.pop("updated_at", None)
    return u

@router.put("/{user_id}")
async def update_user_endpoint(
    user_id: int, 
    user_update: UserUpdate, 
    db: AsyncSession = Depends(get_db), 
    admin=Depends(get_current_admin)
):
    """
    Update a user by ID. Admin-only endpoint.
    """
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Prevent admin from updating themselves through this endpoint
    if user.id == admin.id:
        logger.warning(f"Admin {admin.name} attempted to update themselves through admin endpoint")
        raise HTTPException(
            status_code=400, 
            detail="You cannot update your own account through this endpoint"
        )
    logger.info(f"Admin {admin.name} updating user: {user.name} ({user.phone_number})")
    updated_user = await update_user(db, user, user_update)
    u = updated_user.__dict__.copy()
    u.pop("id", None)
    u.pop("created_at", None)
    u.pop("updated_at", None)
    return u

@router.delete("/{user_id}")
async def delete_user_endpoint(user_id: int, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    """
    Delete a user by ID. Admin-only endpoint.
    """
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deleting themselves
    if user.id == admin.id:
        logger.warning(f"Admin {admin.name} attempted to delete themselves")
        raise HTTPException(
            status_code=400, 
            detail="You cannot delete your own account"
        )
    
    logger.info(f"Admin {admin.name} deleting user: {user.name} ({user.phone_number})")
    await delete_user(db, user)
    return {"msg": "User deleted"} 