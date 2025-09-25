from sqlalchemy import String, Integer, Float, Boolean, DateTime, func, ForeignKey, Index, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
from datetime import datetime
import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.slipper import Slipper

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class Order(Base):
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), 
        default=OrderStatus.PENDING,
        nullable=False,
        index=True
    )
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str] = mapped_column(String(500), nullable=True)
    # transfer_id field removed (was used for payment integration)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    # Indexes for better query performance  
    __table_args__ = (
    Index('idx_orders_user', 'user_id'),
    Index('idx_orders_status', 'status'),
    Index('idx_orders_created', 'created_at'),
    Index('idx_orders_updated', 'updated_at'),
    Index('idx_orders_order_id', 'order_id'),
    # Composite indexes for common queries
    Index('idx_orders_user_status', 'user_id', 'status'),
    Index('idx_orders_user_created', 'user_id', 'created_at'),
    Index('idx_orders_status_created', 'status', 'created_at'),
    Index('idx_orders_total_amount', 'total_amount'),  # For analytics
    )
    
    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, status='{self.status}')>"

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("orders.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    slipper_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("slippers.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="items")
    slipper: Mapped["Slipper"] = relationship("Slipper")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_order_items_order', 'order_id'),
        Index('idx_order_items_slipper', 'slipper_id'),
        # Composite index for order item queries
        Index('idx_order_items_order_slipper', 'order_id', 'slipper_id'),
    )
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, slipper_id={self.slipper_id}, quantity={self.quantity})>"