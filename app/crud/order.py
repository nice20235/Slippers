from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import func, and_
from app.models.order import Order, OrderItem, OrderStatus
from app.models.slipper import Slipper
from app.schemas.order import OrderCreate, OrderUpdate, OrderItemCreate
from typing import Optional, List, Tuple
import logging
from app.models.payment import Payment, PaymentStatus

logger = logging.getLogger(__name__)

async def get_order(db: AsyncSession, order_id: int, load_relationships: bool = True) -> Optional[Order]:
    """Get order by ID with optional relationship loading"""
    query = select(Order).where(Order.id == order_id)
    
    if load_relationships:
        query = query.options(
            joinedload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.slipper)
        )
    
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_orders(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    status: Optional[OrderStatus] = None,
    load_relationships: bool = True
) -> Tuple[List[Order], int]:
    """Get orders with pagination and filters - optimized"""
    # Build base query
    query = select(Order)
    conditions = []
    
    # Apply filters
    if user_id is not None:
        conditions.append(Order.user_id == user_id)
    if status is not None:
        conditions.append(Order.status == status)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Add relationships if needed
    if load_relationships:
        query = query.options(
            joinedload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.slipper)
        )
    
    # Order by created_at for consistent results
    query = query.order_by(Order.created_at.desc())
    
    # Sequential execution to avoid SQLite concurrent operations
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    data_result = await db.execute(query.offset(skip).limit(limit))
    orders = data_result.scalars().all()
    
    return orders, total


async def get_orders_by_payment_statuses(
    db: AsyncSession,
    *,
    statuses: List[PaymentStatus],
    user_id: Optional[int] = None,
    load_relationships: bool = True,
) -> Tuple[List[Tuple[Order, Optional[PaymentStatus]]], int]:
    """Return orders where the latest payment status is in provided statuses.
    If user_id is provided, restrict to that user's orders.
    Returns list of tuples: (Order, latest_payment_status).
    """
    # Subquery to get latest payment per order by created_at
    latest_payment_sq = (
        select(
            Payment.order_id,
            func.max(Payment.created_at).label("max_created"),
        )
        .group_by(Payment.order_id)
        .subquery()
    )

    # Join orders with latest payments
    base = (
        select(Order, Payment.status)
        .join(latest_payment_sq, latest_payment_sq.c.order_id == Order.id, isouter=True)
        .join(
            Payment,
            (Payment.order_id == latest_payment_sq.c.order_id)
            & (Payment.created_at == latest_payment_sq.c.max_created),
            isouter=True,
        )
    )

    conditions = []
    if user_id is not None:
        conditions.append(Order.user_id == user_id)
    if statuses:
        conditions.append(Payment.status.in_(statuses))
    if conditions:
        base = base.where(and_(*conditions))

    base = base.order_by(Order.created_at.desc())

    # Count
    count_query = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Data
    if load_relationships:
        base = base.options(
            joinedload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.slipper),
        )
    rows = (await db.execute(base)).all()
    return rows, total

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
    
    # Create order with temporary placeholder order_id if none provided
    provided_order_id = order.order_id
    db_order = Order(
        order_id=provided_order_id if provided_order_id else "0",
        user_id=order.user_id,
        total_amount=total_amount,
        notes=order.notes,
        status="pending"
    )
    db.add(db_order)
    await db.flush()  # obtain primary key

    # If no order_id provided, set sequential numeric based on primary key
    if not provided_order_id:
        db_order.order_id = str(db_order.id)
        db.add(db_order)

    # Attach items
    for item in order_items:
        item.order_id = db_order.id
        db.add(item)

    await db.commit()
    await db.refresh(db_order)

    # Load relationships for response
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
    """Update an existing order and return with relationships."""
    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
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