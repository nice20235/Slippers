from __future__ import annotations

import os
from typing import List, Tuple
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slipper import SlipperImage, Slipper


def _static_images_dir() -> str:
    # app/services/ -> app/static/images
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../static/images"))


async def ensure_slipper_exists(db: AsyncSession, slipper_id: int) -> Slipper:
    res = await db.execute(select(Slipper).where(Slipper.id == slipper_id))
    slipper = res.scalar_one_or_none()
    if not slipper:
        raise HTTPException(status_code=404, detail="Slipper not found")
    return slipper


async def upload_images_for_slipper(
    db: AsyncSession,
    slipper: Slipper,
    files: List[UploadFile],
) -> Tuple[str | None, List[dict]]:
    """
    Save uploaded image files for a slipper and create DB records.

    - If the slipper has no primary image, the first uploaded becomes primary and sets slipper.image.
    - Ensures a single primary image.

    Returns: (first_image_path, uploaded_images_info)
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=400, detail="Too many images. Maximum 10 images allowed."
        )

    os.makedirs(_static_images_dir(), exist_ok=True)

    # Check if primary exists
    has_primary = False
    res = await db.execute(
        select(SlipperImage.id)
        .where(
            (SlipperImage.slipper_id == slipper.id)
            & (SlipperImage.is_primary == True)  # noqa: E712
        )
        .limit(1)
    )
    has_primary = res.scalar_one_or_none() is not None

    uploaded_images: List[dict] = []
    first_image_path: str | None = None

    for idx, file in enumerate(files):
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            raise HTTPException(
                status_code=400, detail=f"Invalid image format for file {file.filename}"
            )

        filename = f"{uuid4().hex}{ext}"
        abs_path = os.path.join(_static_images_dir(), filename)
        with open(abs_path, "wb") as f:
            f.write(await file.read())
        relative_path = f"/static/images/{filename}"

        make_primary = (not has_primary) and (idx == 0)
        db_img = SlipperImage(
            slipper_id=slipper.id,
            image_path=relative_path,
            is_primary=make_primary,
            order_index=idx,
        )
        db.add(db_img)

        if first_image_path is None:
            first_image_path = relative_path

        uploaded_images.append(
            {
                "image_path": relative_path,
                "is_primary": make_primary,
                "order_index": idx,
            }
        )

    # Set slipper.image if it is empty
    if (not slipper.image) and first_image_path:
        slipper.image = first_image_path
        db.add(slipper)

    # If we just created a primary, ensure only one primary remains
    if (not has_primary) and first_image_path:
        res = await db.execute(
            select(SlipperImage.id)
            .where(
                (SlipperImage.slipper_id == slipper.id)
                & (SlipperImage.image_path == first_image_path)
            )
            .limit(1)
        )
        new_primary_id = res.scalar_one_or_none()
        if new_primary_id:
            await db.execute(
                update(SlipperImage)
                .where(
                    (SlipperImage.slipper_id == slipper.id)
                    & (SlipperImage.id != new_primary_id)
                )
                .values(is_primary=False)
            )

    await db.commit()

    return first_image_path, uploaded_images
