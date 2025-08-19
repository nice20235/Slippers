from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.database import get_db
from app.crud.slipper import get_slipper as get_food, get_slippers as get_foods, create_slipper as create_food, update_slipper as update_food, delete_slipper as delete_food, get_category
from app.schemas.slipper import SlipperCreate as FoodCreate, SlipperUpdate as FoodUpdate, SlipperInDB as FoodInDB
from app.auth.dependencies import get_current_admin
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[FoodInDB])
async def read_foods(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all slippers with optional category filtering and pagination.
    """
    if category_id is not None:
        foods = await get_foods(db, skip=skip, limit=limit, category_id=category_id)
    else:
        foods = await get_foods(db, skip=skip, limit=limit)
    return foods

@router.get("/{food_id}", response_model=FoodInDB)
async def read_food(food_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a specific slipper by ID.
    """
    food = await get_food(db, food_id=food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Food not found")
    return food

@router.post("/", response_model=FoodInDB)
async def create_new_food(
    food: FoodCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Create a new slipper item (Admin only).
    """
    # Verify category exists if category_id is provided
    if food.category_id:
        category = await get_category(db, category_id=food.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
    
    db_food = await create_food(db, food=food)
    return db_food

@router.put("/{food_id}", response_model=FoodInDB)
async def update_existing_food(
    food_id: int,
    food: FoodUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Update a slipper item (Admin only).
    """
    db_food = await get_food(db, food_id=food_id)
    if db_food is None:
        raise HTTPException(status_code=404, detail="Food not found")
    
    # Verify category exists if category_id is provided
    if food.category_id:
        category = await get_category(db, category_id=food.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
    
    return await update_food(db, db_food=db_food, food_update=food)

@router.delete("/{food_id}")
async def delete_existing_food(
    food_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Delete a slipper item (Admin only).
    """
    db_food = await get_food(db, food_id=food_id)
    if db_food is None:
        raise HTTPException(status_code=404, detail="Food not found")
    await delete_food(db, db_food=db_food)
    return {"message": "Food deleted successfully"} 