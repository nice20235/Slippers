from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.cart import Cart, CartItem
from app.models.slipper import Slipper
from app.schemas.cart import CartItemCreate, CartItemUpdate
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Helper to load a cart with items + slippers eagerly
_cart_with_items = lambda: [selectinload(Cart.items).selectinload(CartItem.slipper)]  # noqa: E731

async def _reload_cart(db: AsyncSession, cart_id: int) -> Cart:
    q = await db.execute(
        select(Cart)
        .where(Cart.id == cart_id)
        .options(*_cart_with_items())
    )
    return q.scalar_one()

async def get_or_create_cart(db: AsyncSession, user_id: int) -> Cart:
    q = await db.execute(
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(*_cart_with_items())
    )
    cart = q.scalar_one_or_none()
    if cart:
        return cart
    cart = Cart(user_id=user_id)
    db.add(cart)
    await db.commit()
    return await _reload_cart(db, cart.id)

async def get_cart(db: AsyncSession, user_id: int) -> Optional[Cart]:
    q = await db.execute(
        select(Cart)
        .where(Cart.user_id == user_id)
        .options(*_cart_with_items())
    )
    return q.scalar_one_or_none()

async def add_item(db: AsyncSession, user_id: int, item: CartItemCreate) -> Cart:
    cart = await get_or_create_cart(db, user_id)
    # Ensure slipper exists
    slipper = (await db.execute(select(Slipper).where(Slipper.id == item.slipper_id))).scalar_one_or_none()
    if not slipper:
        raise ValueError("Slipper not found")
    # Merge or add
    for ci in cart.items:
        if ci.slipper_id == item.slipper_id:
            ci.quantity += item.quantity
            db.add(ci)
            break
    else:
        db.add(CartItem(cart_id=cart.id, slipper_id=item.slipper_id, quantity=item.quantity))
    await db.commit()
    return await _reload_cart(db, cart.id)

async def update_item(db: AsyncSession, user_id: int, cart_item_id: int, update: CartItemUpdate) -> Cart:
    cart = await get_or_create_cart(db, user_id)
    target = next((ci for ci in cart.items if ci.id == cart_item_id), None)
    if not target:
        raise ValueError("Cart item not found")
    if update.quantity == 0:
        await db.delete(target)
    else:
        target.quantity = update.quantity
        db.add(target)
    await db.commit()
    return await _reload_cart(db, cart.id)

async def remove_item(db: AsyncSession, user_id: int, cart_item_id: int) -> Cart:
    cart = await get_or_create_cart(db, user_id)
    target = next((ci for ci in cart.items if ci.id == cart_item_id), None)
    if not target:
        raise ValueError("Cart item not found")
    await db.delete(target)
    await db.commit()
    return await _reload_cart(db, cart.id)

async def clear_cart(db: AsyncSession, user_id: int) -> Cart:
    cart = await get_or_create_cart(db, user_id)
    for ci in list(cart.items):
        await db.delete(ci)
    await db.commit()
    return await _reload_cart(db, cart.id)

