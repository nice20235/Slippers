from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.order import OrderInDB, OrderCreate, OrderUpdate
from app.crud.order import get_orders, get_user_orders, get_order, create_order, update_order, delete_order
from app.auth.dependencies import get_current_user, get_current_admin

import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=OrderInDB)
async def create_order_endpoint(order: OrderCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """
    Create a new order. Available to all authenticated users.
    """
    logger.info(f"Creating order for user: {user.name} (Admin: {user.is_admin})")
    # Set the user_id from the authenticated user
    order.user_id = user.id
    return await create_order(db, order)

@router.get("/", response_model=list[OrderInDB])
async def list_orders(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """
    List orders. Admins can see all orders, users can only see their own orders.
    """
    if user.is_admin:
        logger.info(f"Admin {user.name} listing all orders")
        orders, total = await get_orders(db)
        return orders
    else:
        logger.info(f"User {user.name} listing their own orders")
        orders, total = await get_user_orders(db, user.id)
        return orders

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
    return await update_order(db, db_order, order_update)

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
    return {"msg": "Order deleted"} 