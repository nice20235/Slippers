from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from app.models.order import Order, OrderItem, OrderStatus
from app.models.food import Slipper
from app.schemas.order import OrderCreate, OrderUpdate, OrderItemCreate
from typing import Optional, List, Tuple

async def get_order(db: AsyncSession, order_id: int) -> Optional[Order]:
    """Get order by ID with all relationships"""
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.slipper)
        )
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()

async def get_orders(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    status: Optional[OrderStatus] = None
) -> Tuple[List[Order], int]:
    """Get orders with pagination and filters"""
    # Build query
    query = select(Order).options(
        selectinload(Order.user),
        selectinload(Order.items).selectinload(OrderItem.slipper)
    )
    
    # Apply filters
    if user_id is not None:
        query = query.where(Order.user_id == user_id)
    if status is not None:
        query = query.where(Order.status == status)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    result = await db.execute(query.offset(skip).limit(limit))
    orders = result.scalars().all()
    
    return orders, total

async def create_order(db: AsyncSession, order: OrderCreate) -> Order:
    """Create new order with items"""
    # Calculate total amount
    total_amount = 0.0
    order_items = []
    
    for item_data in order.items:
        # Get slipper to verify it exists and get current price
        slipper_result = await db.execute(select(Slipper).where(Slipper.id == item_data.slipper_id))
        slipper = slipper_result.scalar_one_or_none()
        if not slipper:
            raise ValueError(f"Slipper with ID {item_data.slipper_id} not found")
        
        # Use current slipper price
        unit_price = slipper.price
        total_price = unit_price * item_data.quantity
        total_amount += total_price
        
        # Create order item (use slipper_id)
        order_item = OrderItem(
            slipper_id=item_data.slipper_id,
            quantity=item_data.quantity,
            unit_price=unit_price,
            total_price=total_price,
            notes=item_data.notes
        )
        order_items.append(order_item)
    
    # Create order
    db_order = Order(
        user_id=order.user_id,
        total_amount=total_amount,
        notes=order.notes
    )
    db.add(db_order)
    await db.flush()  # Get the order ID
    
    # Set order_id for all items
    for item in order_items:
        item.order_id = db_order.id
        db.add(item)
    
    await db.commit()
    await db.refresh(db_order)
    
    # Load relationships
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.slipper)
        )
        .where(Order.id == db_order.id)
    )
    return result.scalar_one()

async def update_order(db: AsyncSession, db_order: Order, order_update: OrderUpdate) -> Order:
    """Update order"""
    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)
    
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    
    # Load relationships
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.slipper)
        )
        .where(Order.id == db_order.id)
    )
    return result.scalar_one()

async def update_order_status(db: AsyncSession, order_id: int, status: OrderStatus) -> Optional[Order]:
    """Update order status"""
    order = await get_order(db, order_id)
    if not order:
        return None
    
    order.status = status
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    # Load relationships
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.slipper)
        )
        .where(Order.id == order.id)
    )
    return result.scalar_one()

async def delete_order(db: AsyncSession, db_order: Order) -> bool:
    """Delete order (cascade will delete items)"""
    await db.delete(db_order)
    await db.commit()
    return True

async def get_user_orders(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[Order], int]:
    """Get orders for specific user"""
    return await get_orders(db, skip, limit, user_id=user_id) 