from __future__ import annotations

from typing import Any, Dict, List

from app.models.slipper import Slipper, SlipperImage


def slipper_image_to_dict(img: SlipperImage) -> Dict[str, Any]:
    """Serialize SlipperImage ORM object to dict.

    Contract:
    - inputs: SlipperImage
    - outputs: dict with id, image_path, is_primary, alt_text, order_index
    - never raises; missing attrs treated as None
    """
    return {
        "id": getattr(img, "id", None),
        "image_path": getattr(img, "image_path", None),
        "is_primary": bool(getattr(img, "is_primary", False)),
        "alt_text": getattr(img, "alt_text", None),
        "order_index": getattr(img, "order_index", 0),
    }


def _sort_images(images: List[SlipperImage]) -> List[SlipperImage]:
    """Sort images with primary first, then by order_index."""
    try:
        return sorted(images, key=lambda im: (0 if getattr(im, "is_primary", False) else 1, getattr(im, "order_index", 0)))
    except Exception:
        # Fallback: return as-is to avoid breaking response on unusual data
        return list(images)


def slipper_to_dict(s: Slipper, include_images: bool = True) -> Dict[str, Any]:
    """Serialize Slipper ORM object to a response dict used by API.

    Provides consistent shaping for list and detail endpoints.
    """
    item: Dict[str, Any] = {
        "id": s.id,
        "name": s.name,
        "size": s.size,
        "price": s.price,
        "quantity": s.quantity,
        "category_id": s.category_id,
        "category_name": getattr(getattr(s, "category", None), "name", None),
        "image": s.image,
        "is_available": (s.quantity or 0) > 0,
    }

    if include_images and hasattr(s, "images") and isinstance(s.images, list):
        images_sorted = _sort_images(s.images)
        item["images"] = [slipper_image_to_dict(img) for img in images_sorted]
        item["image_gallery"] = [img.image_path for img in images_sorted]
        item["primary_image"] = next((img.image_path for img in images_sorted if getattr(img, "is_primary", False)), s.image)

    return item
