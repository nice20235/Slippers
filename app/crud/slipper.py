from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.food import Slipper, Category
from app.schemas.slipper import SlipperCreate, SlipperUpdate
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


# Slipper CRUD operations
async def get_slipper(db: AsyncSession, slipper_id: int):
	result = await db.execute(
		select(Slipper)
		.options(selectinload(Slipper.category))
		.where(Slipper.id == slipper_id)
	)
	return result.scalar_one_or_none()


async def get_slippers(db: AsyncSession, skip: int = 0, limit: int = 100, category_id: int = None):
	query = select(Slipper).options(selectinload(Slipper.category))
	if category_id:
		query = query.where(Slipper.category_id == category_id)
	result = await db.execute(query.offset(skip).limit(limit))
	return result.scalars().all()


async def create_slipper(db: AsyncSession, slipper_data: dict):
	db_slipper = Slipper(**slipper_data)
	db.add(db_slipper)
	await db.commit()
	await db.refresh(db_slipper)
	# Load the category relationship
	result = await db.execute(
		select(Slipper)
		.options(selectinload(Slipper.category))
		.where(Slipper.id == db_slipper.id)
	)
	return result.scalar_one()


async def update_slipper(db: AsyncSession, db_slipper: Slipper, slipper_update: SlipperUpdate):
	for field, value in slipper_update.model_dump(exclude_unset=True).items():
		setattr(db_slipper, field, value)
	db.add(db_slipper)
	await db.commit()
	await db.refresh(db_slipper)
	# Load the category relationship
	result = await db.execute(
		select(Slipper)
		.options(selectinload(Slipper.category))
		.where(Slipper.id == db_slipper.id)
	)
	return result.scalar_one()


async def delete_slipper(db: AsyncSession, db_slipper: Slipper):
	await db.delete(db_slipper)
	await db.commit()


