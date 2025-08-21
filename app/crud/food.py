from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.food import Slipper as Food, Category
from app.schemas.slipper import SlipperCreate as FoodCreate, SlipperUpdate as FoodUpdate
from app.schemas.category import CategoryCreate, CategoryUpdate

# Category CRUD operations
async def get_category(db: AsyncSession, category_id: int):
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()

async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Category).offset(skip).limit(limit))
    return result.scalars().all()

async def create_category(db: AsyncSession, category: CategoryCreate):
    db_category = Category(**category.model_dump())
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category

async def update_category(db: AsyncSession, db_category: Category, category_update: CategoryUpdate):
    for field, value in category_update.model_dump(exclude_unset=True).items():
        setattr(db_category, field, value)
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category

async def delete_category(db: AsyncSession, db_category: Category):
    await db.delete(db_category)
    await db.commit()

# Slipper CRUD operations (kept path for compatibility with imports in endpoints)
async def get_food(db: AsyncSession, food_id: int):
    result = await db.execute(
        select(Food)
        .options(selectinload(Food.category))
        .where(Food.id == food_id)
    )
    return result.scalar_one_or_none()

async def get_foods(db: AsyncSession, skip: int = 0, limit: int = 100, category_id: int = None):
    query = select(Food).options(selectinload(Food.category))
    if category_id:
        query = query.where(Food.category_id == category_id)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

async def create_food(db: AsyncSession, food: FoodCreate):
    db_food = Food(**food.model_dump())
    db.add(db_food)
    await db.commit()
    await db.refresh(db_food)
    # Load the category relationship
    result = await db.execute(
        select(Food)
        .options(selectinload(Food.category))
        .where(Food.id == db_food.id)
    )
    return result.scalar_one()

async def update_food(db: AsyncSession, db_food: Food, food_update: FoodUpdate):
    for field, value in food_update.model_dump(exclude_unset=True).items():
        setattr(db_food, field, value)
    db.add(db_food)
    await db.commit()
    await db.refresh(db_food)
    # Load the category relationship
    result = await db.execute(
        select(Food)
        .options(selectinload(Food.category))
        .where(Food.id == db_food.id)
    )
    return result.scalar_one()

async def delete_food(db: AsyncSession, db_food: Food):
    await db.delete(db_food)
    await db.commit() 