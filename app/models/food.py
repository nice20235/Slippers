from sqlalchemy import String, Integer, Float, Boolean, DateTime, func, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
from datetime import datetime

class Category(Base):
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    
    # Relationship with slippers
    slippers: Mapped[list["Slipper"]] = relationship("Slipper", back_populates="category", cascade="all, delete-orphan")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_categories_name', 'name'),
        Index('idx_categories_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"

class Slipper(Base):
    __tablename__ = "slippers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    image: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    price: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    category_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("categories.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
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
    
    # Relationship with category
    category: Mapped[Category] = relationship("Category", back_populates="slippers")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_slippers_name', 'name'),
        Index('idx_slippers_size', 'size'),
        Index('idx_slippers_price', 'price'),
        Index('idx_slippers_quantity', 'quantity'),
        Index('idx_slippers_category', 'category_id'),
    )
    
    def __repr__(self):
        return f"<Slipper(id={self.id}, name='{self.name}', size='{self.size}', price={self.price})>"