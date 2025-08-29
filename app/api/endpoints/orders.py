from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.order import (
    OrderInDB,
    OrderCreate,
    OrderUpdate,
    OrderCreatePublic,
    OrderPublic,
    OrderItemCreate,
)
from app.crud.order import get_orders, get_user_orders, get_order, create_order, update_order, delete_order
from app.auth.dependencies import get_current_user, get_current_admin
from app.core.cache import cached
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=OrderPublic)
async def create_order_endpoint(order: OrderCreatePublic, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """
    Create a new order. Available to all authenticated users.
    """
    logger.info(f"Creating order for user: {user.name} (Admin: {user.is_admin})")
    # Set the user_id from the authenticated user
    internal_order = OrderCreate(
        order_id=None,
        user_id=user.id,
        items=[
            OrderItemCreate(
                slipper_id=it.slipper_id,
                quantity=it.quantity,
                unit_price=1.0,  # dummy value; real price fetched in CRUD
                notes=it.notes,
            )
            for it in order.items
        ],
        notes=order.notes,
    )
    new_order = await create_order(db, internal_order)
    
    # Clear cache after creating order
    from app.core.cache import invalidate_cache_pattern
    await invalidate_cache_pattern("orders:")
    
    return OrderPublic(
        order_id=new_order.order_id,
        status=new_order.status,
        total_amount=new_order.total_amount,
        notes=new_order.notes,
        created_at=new_order.created_at,
        items=[
            {
                "slipper_id": oi.slipper_id,
                "quantity": oi.quantity,
                "unit_price": oi.unit_price,
                "total_price": oi.total_price,
                "notes": oi.notes,
            }
            for oi in new_order.items
        ],
    )

@router.get("/")
@cached(ttl=60, key_prefix="orders")
async def list_orders(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """List orders.
    - Regular user: only their own orders.
    - Admin: all users' orders.
    Pagination & status filtering removed per request.
    """
    try:
        if user.is_admin:
            logger.info(f"Admin {user.name} listing ALL orders")
            orders, total = await get_orders(db, skip=0, limit=100000, load_relationships=True)
        else:
            logger.info(f"User {user.name} listing OWN orders")
            orders, total = await get_orders(db, skip=0, limit=100000, user_id=user.id, load_relationships=True)

        return [
            {
                "id": order.id,
                "user_id": order.user_id,
                "user_name": order.user.name if hasattr(order, 'user') and order.user else None,
                "status": order.status.value,
                "total_amount": order.total_amount,
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            }
            for order in orders
        ]
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        raise HTTPException(status_code=500, detail="Error fetching orders")

@router.get("/{order_id}", response_model=OrderInDB)
@cached(ttl=300, key_prefix="order")
async def get_order_endpoint(
    order_id: int, 
    db: AsyncSession = Depends(get_db), 
    user=Depends(get_current_user)
):
    """Get a specific order by ID"""
    try:
        db_order = await get_order(db, order_id, load_relationships=True)
        if not db_order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Check permissions
        if not user.is_admin and db_order.user_id != user.id:
            logger.warning(f"User {user.name} attempted to access order {order_id} belonging to user {db_order.user_id}")
            raise HTTPException(status_code=403, detail="Not authorized to access this order")
        
        return db_order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching order")

@router.put("/{order_id}", response_model=OrderInDB)
async def update_order_endpoint(order_id: int, order_update: OrderUpdate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """
    Update an order. Admins can update any order, users can only update their own orders.
    """
    db_order = await get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check permissions
    if not user.is_admin and db_order.user_id != user.id:
        logger.warning(f"User {user.name} (Admin: {user.is_admin}) attempted to update order {order_id} belonging to user {db_order.user_id}")
        raise HTTPException(
            status_code=403, 
            detail="You can only update your own orders"
        )
    
    logger.info(f"Updating order {order_id} by user: {user.name} (Admin: {user.is_admin})")
    updated_order = await update_order(db, db_order, order_update)
    
    # Clear cache after updating order
    from app.core.cache import invalidate_cache_pattern
    await invalidate_cache_pattern("orders:")
    await invalidate_cache_pattern(f"order:{order_id}:")
    
    return updated_order

@router.delete("/{order_id}")
async def delete_order_endpoint(order_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """
    Delete an order. Admins can delete any order, users can only delete their own orders.
    """
    db_order = await get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check permissions
    if not user.is_admin and db_order.user_id != user.id:
        logger.warning(f"User {user.name} (Admin: {user.is_admin}) attempted to delete order {order_id} belonging to user {db_order.user_id}")
        raise HTTPException(
            status_code=403, 
            detail="You can only delete your own orders"
        )
    
    logger.info(f"Deleting order {order_id} by user: {user.name} (Admin: {user.is_admin})")
    await delete_order(db, db_order)
    
    # Clear cache after deleting order
    from app.core.cache import invalidate_cache_pattern
    await invalidate_cache_pattern("orders:")
    await invalidate_cache_pattern(f"order:{order_id}:")
    
    return {"msg": "Order deleted"} 