from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.database import get_db
from app.crud.slipper import (
    get_category, get_categories, create_category, update_category, delete_category
)
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryInDB
from app.auth.dependencies import get_current_admin

router = APIRouter()

@router.get("/", response_model=List[CategoryInDB])
async def read_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all categories with pagination.
    """
    categories = await get_categories(db, skip=skip, limit=limit)
    return categories

@router.get("/{category_id}", response_model=CategoryInDB)
async def read_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a specific category by ID.
    """
    category = await get_category(db, category_id=category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.post("/", response_model=CategoryInDB)
async def create_new_category(
    category: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Create a new category (Admin only).
    """
    db_category = await create_category(db, category=category)
    return db_category

@router.put("/{category_id}", response_model=CategoryInDB)
async def update_existing_category(
    category_id: int,
    category: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Update a category (Admin only).
    """
    db_category = await get_category(db, category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return await update_category(db, db_category=db_category, category_update=category)

@router.delete("/{category_id}")
async def delete_existing_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Delete a category (Admin only).
    """
    db_category = await get_category(db, category_id=category_id)
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    await delete_category(db, db_category=db_category)
    return {"message": "Category deleted successfully"} 