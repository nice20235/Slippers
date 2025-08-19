from fastapi import status
# Эндпоинт для загрузки изображения к тапочке

# --- upload image endpoint moved below router definition ---
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.database import get_db
from app.crud.slipper import get_slipper, get_slippers, create_slipper, update_slipper, delete_slipper, get_category
from fastapi import UploadFile, File, Form
import os
from uuid import uuid4
from app.auth.dependencies import get_current_admin
import logging


# Set up logging
logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/")
async def read_slippers(
	skip: int = Query(0, ge=0),
	limit: int = Query(100, ge=1, le=100),
	category_id: Optional[int] = Query(None, description="Filter by category ID"),
	db: AsyncSession = Depends(get_db)
):
	"""
	Get all slippers with optional category filtering and pagination.
	"""
	if category_id is not None:
		slippers = await get_slippers(db, skip=skip, limit=limit, category_id=category_id)
	else:
		slippers = await get_slippers(db, skip=skip, limit=limit)
	return [
		{
			"id": s.id,
			"name": s.name,
			"size": s.size,
			"price": s.price,
			"quantity": s.quantity,
			"category_id": s.category_id,
			"image": s.image
		} for s in slippers
	]


@router.get("/{slipper_id}")
async def read_slipper(slipper_id: int, db: AsyncSession = Depends(get_db)):
	"""
	Get a specific slipper by ID.
	"""
	slipper = await get_slipper(db, slipper_id=slipper_id)
	if slipper is None:
		raise HTTPException(status_code=404, detail="Slipper not found")
	return {
		"id": slipper.id,
		"name": slipper.name,
		"size": slipper.size,
		"price": slipper.price,
		"quantity": slipper.quantity,
		"category_id": slipper.category_id,
		"image": slipper.image
	}





from app.schemas.slipper import SlipperCreate

@router.post("/", summary="Создать тапочку (без картинки)")
async def create_new_slipper(
	slipper: SlipperCreate,
	db: AsyncSession = Depends(get_db),
	current_admin: dict = Depends(get_current_admin)
):
	"""
	Создать новую тапочку (admin only) через JSON. Картинку загружать отдельным запросом.
	Пример запроса (application/json):
	{
	  "name": "Cozy Home Slipper",
	  "size": "42",
	  "price": 25.99,
	  "quantity": 50,
	  "category_id": 1
	}
	"""
	# Проверяем категорию
	if slipper.category_id:
		category = await get_category(db, category_id=slipper.category_id)
		if not category:
			raise HTTPException(status_code=404, detail="Category not found")

	from app.models.food import Slipper
	# image временно пустая строка (NOT NULL в БД), затем обновляется через /upload-image
	db_slipper = Slipper(
		name=slipper.name,
		size=slipper.size,
		price=slipper.price,
		quantity=slipper.quantity,
		category_id=slipper.category_id,
		image=""
	)
	db.add(db_slipper)
	await db.commit()
	await db.refresh(db_slipper)
	return {
		"id": db_slipper.id,
		"name": db_slipper.name,
		"size": db_slipper.size,
		"price": db_slipper.price,
		"quantity": db_slipper.quantity,
		"category_id": db_slipper.category_id,
		"image": db_slipper.image
	}


@router.put("/{slipper_id}")
async def update_existing_slipper(
	slipper_id: int,
	slipper: dict,
	db: AsyncSession = Depends(get_db),
	current_admin: dict = Depends(get_current_admin)
):
	"""
	Update a slipper item (Admin only).
	"""
	db_slipper = await update_slipper(db, slipper_id, slipper)
	if db_slipper is None:
		raise HTTPException(status_code=404, detail="Slipper not found")
	return {
		"id": db_slipper.id,
		"name": db_slipper.name,
		"size": db_slipper.size,
		"price": db_slipper.price,
		"quantity": db_slipper.quantity,
		"category_id": db_slipper.category_id,
		"image": db_slipper.image
	}
async def update_existing_slipper(
	slipper_id: int,
	slipper: dict,
	db: AsyncSession = Depends(get_db),
	current_admin: dict = Depends(get_current_admin)
):
	"""
	Update a slipper item (Admin only).
	"""
	db_slipper = await get_slipper(db, slipper_id=slipper_id)
	if db_slipper is None:
		raise HTTPException(status_code=404, detail="Slipper not found")
	
	# Verify category exists if category_id is provided
	if slipper.category_id:
		category = await get_category(db, category_id=slipper.category_id)
		if not category:
			raise HTTPException(status_code=404, detail="Category not found")
	
	return await update_slipper(db, db_slipper=db_slipper, slipper_update=slipper)


@router.delete("/{slipper_id}")
async def delete_existing_slipper(
	slipper_id: int,
	db: AsyncSession = Depends(get_db),
	current_admin: dict = Depends(get_current_admin)
):
	"""
	Delete a slipper item (Admin only).
	"""
	db_slipper = await get_slipper(db, slipper_id=slipper_id)
	if db_slipper is None:
		raise HTTPException(status_code=404, detail="Slipper not found")
	await delete_slipper(db, db_slipper=db_slipper)
	return {"message": "Slipper deleted successfully"}


@router.post("/{slipper_id}/upload-image", summary="Загрузить изображение для тапочки")
async def upload_slipper_image(
    slipper_id: int,
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Загрузить/обновить изображение для существующей тапочки по id.
    """
    from app.models.food import Slipper
    slipper = await get_slipper(db, slipper_id=slipper_id)
    if not slipper:
        raise HTTPException(status_code=404, detail="Slipper not found")

    ext = os.path.splitext(image.filename)[1]
    if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        raise HTTPException(status_code=400, detail="Invalid image format")
    filename = f"{uuid4().hex}{ext}"
    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../static/images'))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as f:
        f.write(await image.read())
    relative_path = f"/static/images/{filename}"

    slipper.image = relative_path
    db.add(slipper)
    await db.commit()
    await db.refresh(slipper)
    return {"id": slipper.id, "image": slipper.image}


