from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import os
import logging

from app.db.database import get_db
from app.auth.dependencies import get_current_admin
from app.core.cache import cached
from app.crud.slipper import (
    get_slipper,
    get_slippers,
    update_slipper,
    delete_slipper,
    get_category,
)
from app.schemas.slipper import SlipperCreate, SlipperUpdate
from app.core.serializers import slipper_to_dict


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
@cached(ttl=300, key_prefix="slippers")
async def read_slippers(
    skip: int = Query(0, ge=0, description="Skip items for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Limit items per page"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    search: Optional[str] = Query(None, description="Search in name and size"),
    sort: str = Query(
        "id_desc",
        description="Sort order: id_asc,id_desc,name_asc,name_desc,price_asc,price_desc,created_asc,created_desc",
    ),
    include_images: bool = Query(
        True, description="Include images array for each slipper"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get all slippers with filtering, pagination, search and sorting."""
    try:
        slippers, total = await get_slippers(
            db,
            skip=skip,
            limit=limit,
            category_id=category_id,
            search=search,
            sort=sort,
            load_images=include_images,
        )

        items = []
        for s in slippers:
            items.append(slipper_to_dict(s, include_images=include_images))

        return {
            "items": items,
            "total": total,
            "page": (skip // limit) + 1,
            "pages": (total + limit - 1) // limit,
            "has_next": skip + limit < total,
            "has_prev": skip > 0,
            "sort": sort,
        }
    except Exception as e:
        logger.error(f"Error fetching slippers: {e}")
        raise HTTPException(status_code=500, detail="Error fetching slippers")


@router.get("/{slipper_id}")
@cached(ttl=600, key_prefix="slipper")
async def read_slipper(
    slipper_id: int,
    include_images: bool = Query(True, description="Include slipper images"),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific slipper by ID with optional image loading."""
    try:
        slipper = await get_slipper(
            db, slipper_id=slipper_id, load_images=include_images
        )
        if slipper is None:
            raise HTTPException(status_code=404, detail="Slipper not found")

        response = slipper_to_dict(slipper, include_images=include_images)

        # Optional timestamps
        if hasattr(slipper, "created_at") and slipper.created_at is not None:
            try:
                response["created_at"] = slipper.created_at.isoformat()  # type: ignore[attr-defined]
            except Exception:
                pass
        if hasattr(slipper, "updated_at") and slipper.updated_at is not None:
            try:
                response["updated_at"] = slipper.updated_at.isoformat()  # type: ignore[attr-defined]
            except Exception:
                pass

        # response already includes images when requested; timestamps are added below

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching slipper {slipper_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching slipper")


@router.post("/", summary="Создать тапочку (без картинки)")
async def create_new_slipper(
    slipper: SlipperCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """
    Создать новую тапочку (admin only) через JSON. Картинку загружать отдельным запросом.
    """
    # Проверяем категорию
    if slipper.category_id:
        category = await get_category(db, category_id=slipper.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    from app.models.slipper import Slipper

    db_slipper = Slipper(
        name=slipper.name,
        size=slipper.size,
        price=slipper.price,
        quantity=slipper.quantity,
        category_id=slipper.category_id,
        image="",
    )
    db.add(db_slipper)
    await db.commit()
    await db.refresh(db_slipper)

    from app.core.cache import invalidate_cache_pattern

    await invalidate_cache_pattern("slippers:")

    return {
        "id": db_slipper.id,
        "name": db_slipper.name,
        "size": db_slipper.size,
        "price": db_slipper.price,
        "quantity": db_slipper.quantity,
        "category_id": db_slipper.category_id,
        "image": db_slipper.image,
    }


@router.put("/{slipper_id}")
async def update_existing_slipper(
    slipper_id: int,
    slipper: SlipperUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """
    Update a slipper item (Admin only).
    """
    # Load existing slipper
    existing = await get_slipper(db, slipper_id=slipper_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Slipper not found")
    # Update with provided partial fields
    db_slipper = await update_slipper(db, existing, slipper)

    # Clear cache after updating slipper
    from app.core.cache import invalidate_cache_pattern

    await invalidate_cache_pattern("slippers:")
    await invalidate_cache_pattern(f"slipper_id={slipper_id}")

    return {
        "id": db_slipper.id,
        "name": db_slipper.name,
        "size": db_slipper.size,
        "price": db_slipper.price,
        "quantity": db_slipper.quantity,
        "category_id": db_slipper.category_id,
        "image": db_slipper.image,
    }


@router.delete("/{slipper_id}")
async def delete_existing_slipper(
    slipper_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """
    Delete a slipper item (Admin only).
    """
    try:
        db_slipper = await get_slipper(db, slipper_id=slipper_id)
        if db_slipper is None:
            raise HTTPException(status_code=404, detail="Slipper not found")

        await delete_slipper(db, db_slipper=db_slipper)

        from app.core.cache import invalidate_cache_pattern

        await invalidate_cache_pattern("slippers:")
        await invalidate_cache_pattern(f"slipper_id={slipper_id}")

        return {"message": "Slipper deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting slipper {slipper_id}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting slipper")


@router.post(
    "/{slipper_id}/upload-images/",
    summary="Загрузить несколько изображений для тапочки",
)
async def upload_slipper_images(
    slipper_id: int,
    images: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """Upload one or many images for a slipper. First image becomes main image if not set."""
    from app.services.slippers_images import (
        ensure_slipper_exists,
        upload_images_for_slipper,
    )

    slipper = await ensure_slipper_exists(db, slipper_id)
    _, uploaded_images = await upload_images_for_slipper(db, slipper, images)

    from app.core.cache import invalidate_cache_pattern

    await invalidate_cache_pattern("slippers:")
    await invalidate_cache_pattern(f"slipper_id={slipper_id}")

    return {
        "slipper_id": slipper_id,
        "uploaded_images": uploaded_images,
        "total_uploaded": len(uploaded_images),
    }


@router.get("/{slipper_id}/images", summary="Получить все изображения тапочки")
async def get_slipper_images(slipper_id: int, db: AsyncSession = Depends(get_db)):
    """Получить все изображения для конкретной тапочки."""
    from app.models.slipper import SlipperImage
    from sqlalchemy import select, asc

    slipper = await get_slipper(db, slipper_id=slipper_id)
    if not slipper:
        raise HTTPException(status_code=404, detail="Slipper not found")

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
                "created_at": img.created_at,
            }
            for img in images
        ],
        "total_images": len(images),
    }


@router.delete("/{slipper_id}/images/{image_id}", summary="Удалить изображение тапочки")
async def delete_slipper_image(
    slipper_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """Удалить конкретное изображение тапочки."""
    from app.models.slipper import SlipperImage
    from sqlalchemy import select

    result = await db.execute(
        select(SlipperImage)
        .where(SlipperImage.id == image_id)
        .where(SlipperImage.slipper_id == slipper_id)
    )
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        file_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "../../", image.image_path.lstrip("/")
            )
        )
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.warning(f"Failed to delete physical file {image.image_path}: {e}")

    await db.delete(image)
    await db.commit()

    from app.core.cache import invalidate_cache_pattern

    await invalidate_cache_pattern("slippers:")
    await invalidate_cache_pattern(f"slipper_id={slipper_id}")

    return {"message": "Image deleted successfully", "deleted_image_id": image_id}
