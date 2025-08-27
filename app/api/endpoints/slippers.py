from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.database import get_db
from app.crud.slipper import get_slipper, get_slippers, create_slipper, update_slipper, delete_slipper, get_category
from fastapi import UploadFile, File, Form
import os
from uuid import uuid4
from app.auth.dependencies import get_current_admin
from app.core.cache import cached
import logging


# Set up logging
logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/")
@cached(ttl=300, key_prefix="slippers")
async def read_slippers(
	skip: int = Query(0, ge=0, description="Skip items for pagination"),
	limit: int = Query(20, ge=1, le=100, description="Limit items per page"),
	category_id: Optional[int] = Query(None, description="Filter by category ID"),
	search: Optional[str] = Query(None, description="Search in name and size"),
	sort: str = Query("id_desc", description="Sort order: id_asc,id_desc,name_asc,name_desc,price_asc,price_desc,created_asc,created_desc"),
	db: AsyncSession = Depends(get_db)
):
	"""
	Get all slippers with filtering, pagination and search.
	Optimized with concurrent count/data queries.
	"""
	try:
		slippers, total = await get_slippers(
			db, 
			skip=skip, 
			limit=limit, 
			category_id=category_id,
			search=search,
			sort=sort
		)
		
		# Optimized response structure
		items = []
		for s in slippers:
			items.append({
				"id": s.id,
				"name": s.name,
				"size": s.size,
				"price": s.price,
				"quantity": s.quantity,
				"category_id": s.category_id,
				"category_name": s.category.name if s.category else None,
				"image": s.image,
				"is_available": s.quantity > 0
			})
		
		return {
			"items": items,
			"total": total,
			"page": (skip // limit) + 1,
			"pages": (total + limit - 1) // limit,
			"has_next": skip + limit < total,
			"has_prev": skip > 0,
			"sort": sort
		}
		
	except Exception as e:
		logger.error(f"Error fetching slippers: {e}")
		raise HTTPException(status_code=500, detail="Error fetching slippers")


@router.get("/{slipper_id}")
@cached(ttl=600, key_prefix="slipper")
async def read_slipper(
	slipper_id: int, 
	include_images: bool = Query(False, description="Include slipper images"),
	db: AsyncSession = Depends(get_db)
):
	"""
	Get a specific slipper by ID with optional image loading.
	"""
	try:
		slipper = await get_slipper(db, slipper_id=slipper_id, load_images=include_images)
		if slipper is None:
			raise HTTPException(status_code=404, detail="Slipper not found")
		
		response = {
			"id": slipper.id,
			"name": slipper.name,
			"size": slipper.size,
			"price": slipper.price,
			"quantity": slipper.quantity,
			"category_id": slipper.category_id,
			"category_name": slipper.category.name if slipper.category else None,
			"image": slipper.image,
			"is_available": slipper.quantity > 0,
			"created_at": slipper.created_at.isoformat(),
			"updated_at": slipper.updated_at.isoformat() if slipper.updated_at else None
		}
		
		if include_images and hasattr(slipper, 'images'):
			response["images"] = [
				{
					"id": img.id,
					"image_path": img.image_path,
					"is_primary": img.is_primary,
					"alt_text": img.alt_text,
					"order_index": img.order_index
				} for img in slipper.images
			]
		
		return response
		
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error fetching slipper {slipper_id}: {e}")
		raise HTTPException(status_code=500, detail="Error fetching slipper")





from app.schemas.slipper import SlipperCreate, SlipperUpdate

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
	
	# Clear cache after creating slipper
	from app.core.cache import invalidate_cache_pattern
	await invalidate_cache_pattern("slippers:")
	
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
	slipper: SlipperUpdate,
	db: AsyncSession = Depends(get_db),
	current_admin: dict = Depends(get_current_admin)
):
	"""
	Update a slipper item (Admin only).
	"""
	# Load existing slipper
	existing = await get_slipper(db, slipper_id=slipper_id)
	if existing is None:
		raise HTTPException(status_code=404, detail="Slipper not found")
	# Build update model from provided fields
	# Update with provided partial fields
	db_slipper = await update_slipper(db, existing, slipper)
	
	# Clear cache after updating slipper
	from app.core.cache import invalidate_cache_pattern
	await invalidate_cache_pattern("slippers:")
	await invalidate_cache_pattern(f"slipper:{slipper_id}:")
	
	return {
		"id": db_slipper.id,
		"name": db_slipper.name,
		"size": db_slipper.size,
		"price": db_slipper.price,
		"quantity": db_slipper.quantity,
		"category_id": db_slipper.category_id,
	"image": db_slipper.image
	}


@router.delete("/{slipper_id}")
async def delete_existing_slipper(
	slipper_id: int,
	db: AsyncSession = Depends(get_db),
	current_admin: dict = Depends(get_current_admin)
):
	"""
	Delete a slipper item (Admin only).
	"""
	try:
		db_slipper = await get_slipper(db, slipper_id=slipper_id)
		if db_slipper is None:
			raise HTTPException(status_code=404, detail="Slipper not found")
		
		await delete_slipper(db, db_slipper=db_slipper)
		
		# Clear cache after deleting slipper
		from app.core.cache import invalidate_cache_pattern
		await invalidate_cache_pattern("slippers:")
		await invalidate_cache_pattern(f"slipper:{slipper_id}:")
		
		return {"message": "Slipper deleted successfully"}
		
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error deleting slipper {slipper_id}: {e}")
		raise HTTPException(status_code=500, detail="Error deleting slipper")



@router.post("/{slipper_id}/upload-images", summary="Загрузить несколько изображений для тапочки")
async def upload_slipper_images(
    slipper_id: int,
    images: List[UploadFile] = File(...),
    is_primary: List[bool] = Form(default=[]),
    alt_texts: List[str] = Form(default=[]),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Загрузить несколько изображений для тапочки.
    - images: Список файлов изображений
    - is_primary: Список булевых значений (какое изображение основное)
    - alt_texts: Список alt-текстов для изображений
    """
    from app.models.food import Slipper, SlipperImage
    
    # Проверяем существование тапочки
    slipper = await get_slipper(db, slipper_id=slipper_id)
    if not slipper:
        raise HTTPException(status_code=404, detail="Slipper not found")
    
    if len(images) > 10:  # Ограничиваем количество изображений
        raise HTTPException(status_code=400, detail="Too many images. Maximum 10 images allowed.")
    
    uploaded_images = []
    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../static/images'))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Загружаем каждое изображение
    for i, image in enumerate(images):
        # Проверяем формат файла
        ext = os.path.splitext(image.filename)[1]
        if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            raise HTTPException(status_code=400, detail=f"Invalid image format for file {image.filename}")
        
        # Генерируем уникальное имя файла
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(upload_dir, filename)
        
        # Сохраняем файл
        with open(file_path, "wb") as f:
            f.write(await image.read())
        
        relative_path = f"/static/images/{filename}"
        
        # Определяем является ли изображение основным
        primary = is_primary[i] if i < len(is_primary) else False
        alt_text = alt_texts[i] if i < len(alt_texts) else None
        
        # Создаем запись в БД
        slipper_image = SlipperImage(
            slipper_id=slipper_id,
            image_path=relative_path,
            is_primary=primary,
            alt_text=alt_text,
            order_index=i
        )
        db.add(slipper_image)
        
        uploaded_images.append({
            "image_path": relative_path,
            "is_primary": primary,
            "alt_text": alt_text,
            "order_index": i
        })
    
    await db.commit()
    
    return {
        "slipper_id": slipper_id,
        "uploaded_images": uploaded_images,
        "total_uploaded": len(uploaded_images)
    }


@router.get("/{slipper_id}/images", summary="Получить все изображения тапочки")
async def get_slipper_images(
    slipper_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить все изображения для конкретной тапочки.
    """
    from app.models.food import SlipperImage
    from sqlalchemy import select, asc
    
    # Проверяем существование тапочки
    slipper = await get_slipper(db, slipper_id=slipper_id)
    if not slipper:
        raise HTTPException(status_code=404, detail="Slipper not found")
    
    # Получаем все изображения, отсортированные по порядку
    result = await db.execute(
        select(SlipperImage)
        .where(SlipperImage.slipper_id == slipper_id)
        .order_by(asc(SlipperImage.order_index))
    )
    images = result.scalars().all()
    
    return {
        "slipper_id": slipper_id,
        "images": [
            {
                "id": img.id,
                "image_path": img.image_path,
                "is_primary": img.is_primary,
                "alt_text": img.alt_text,
                "order_index": img.order_index,
                "created_at": img.created_at
            }
            for img in images
        ],
        "total_images": len(images)
    }


@router.delete("/{slipper_id}/images/{image_id}", summary="Удалить изображение тапочки")
async def delete_slipper_image(
    slipper_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Удалить конкретное изображение тапочки.
    """
    from app.models.food import SlipperImage
    from sqlalchemy import select
    
    # Получаем изображение
    result = await db.execute(
        select(SlipperImage)
        .where(SlipperImage.id == image_id)
        .where(SlipperImage.slipper_id == slipper_id)
    )
    image = result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Удаляем физический файл
    try:
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../', image.image_path.lstrip('/')))
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.warning(f"Failed to delete physical file {image.image_path}: {e}")
    
    # Удаляем запись из БД
    await db.delete(image)
    await db.commit()
    
    return {"message": "Image deleted successfully", "deleted_image_id": image_id}


