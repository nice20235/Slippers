#!/usr/bin/env python3
"""
Slippers Order System - Complete Initialization Script
This script sets up the entire system including database, sample data, and admin user.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.db.database import init_db, AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.user import create_user, promote_to_admin
from app.crud.food import create_category, create_food
from app.schemas.user import UserCreate
from app.schemas.category import CategoryCreate
from app.schemas.slipper import SlipperCreate as FoodCreate

# Sample data
SAMPLE_CATEGORIES = [
    {"name": "Appetizers", "description": "Start your meal with our delicious appetizers"},
    {"name": "Main Courses", "description": "Our signature main dishes"},
    {"name": "Desserts", "description": "Sweet endings to your meal"},
    {"name": "Beverages", "description": "Refreshing drinks and beverages"},
    {"name": "Salads", "description": "Fresh and healthy salad options"},
]

SAMPLE_FOODS = [
    {"image": "https://example.com/slippers/men1.jpg", "name": "Men Classic Slipper", "size": "42", "price": 19.99, "quantity": 25, "category_name": "Men"},
    {"image": "https://example.com/slippers/women1.jpg", "name": "Women Cozy Slipper", "size": "38", "price": 21.99, "quantity": 30, "category_name": "Women"},
    {"image": "https://example.com/slippers/kids1.jpg", "name": "Kids Fun Slipper", "size": "30", "price": 14.99, "quantity": 40, "category_name": "Kids"},
]

async def create_sample_categories(db: AsyncSession):
    """Create sample categories"""
    print("📂 Creating sample categories...")
    categories = {}
    
    for cat_data in SAMPLE_CATEGORIES:
        category = CategoryCreate(**cat_data)
        db_category = await create_category(db, category)
        categories[cat_data["name"]] = db_category
        print(f"  ✅ Created category: {db_category.name}")
    
    return categories

async def create_sample_foods(db: AsyncSession, categories):
    """Create sample foods"""
    print("👟 Creating sample slippers...")
    
    for food_data in SAMPLE_FOODS:
        category_name = food_data.pop("category_name")
        category = categories.get(category_name)
        
        if category:
            food_data["category_id"] = category.id
            food = FoodCreate(**food_data)
            db_food = await create_food(db, food)
            print(f"  ✅ Created slipper: {db_food.name} (${db_food.price}) size {db_food.size}")
        else:
            print(f"  ⚠️  Category '{category_name}' not found for slipper: {food_data['name']}")

async def create_admin_user(db: AsyncSession):
    """Create default admin user"""
    print("👤 Creating admin user...")
    
    # Admin user details
    admin_name = "Admin"
    admin_surname = "User"
    admin_phone = "+1234567890"
    admin_password = "admin123"
    
    # Check if admin already exists
    from app.crud.user import get_user_by_phone_number
    existing_admin = await get_user_by_phone_number(db, admin_phone)
    
    if existing_admin:
        if existing_admin.is_admin:
            print(f"  ✅ Admin user already exists: {admin_name} {admin_surname}")
            return existing_admin
        else:
            # Promote existing user to admin
            admin_user = await promote_to_admin(db, admin_name)
            print(f"  ✅ Promoted user to admin: {admin_name} {admin_surname}")
            return admin_user
    else:
        # Create new admin user
        admin_data = UserCreate(
            name=admin_name,
            surname=admin_surname,
            phone_number=admin_phone,
            password=admin_password,
            confirm_password=admin_password,
            is_admin=True
        )
        admin_user = await create_user(db, admin_data)
        print(f"  ✅ Created admin user: {admin_name} {admin_surname}")
        print(f"  📱 Phone: {admin_phone}")
        print(f"  🔑 Password: {admin_password}")
        return admin_user

async def main():
    """Main initialization function"""
    print("🚀 Initializing Slippers Order System...")
    print("=" * 50)
    
    try:
        # Initialize database
        print("🗄️  Initializing database...")
        await init_db()
        print("  ✅ Database initialized successfully!")
        
        # Create sample data
        async with AsyncSessionLocal() as db:
            # Create categories
            categories = await create_sample_categories(db)
            
            # Create foods
            await create_sample_foods(db, categories)
            
            # Create admin user
            admin_user = await create_admin_user(db)
        
        print("\n" + "=" * 50)
        print("✅ System initialization completed successfully!")
        print("\n📋 Summary:")
        print(f"  • Database: slippers.db")
        print(f"  • Categories: {len(categories)}")
        print(f"  • Slippers: {len(SAMPLE_FOODS)}")
        if admin_user:
            print(f"  • Admin user: {admin_user.name} {admin_user.surname}")
        else:
            print(f"  • Admin user: Not created")
        
        print("\n🔧 Next steps:")
        print("  1. Start the FastAPI server: python -m uvicorn app.main:app --reload")
        print("  2. Access the API documentation: http://localhost:8000/docs")
        print("  3. Login with admin credentials:")
        print("     • Name: Admin")
        print("     • Password: admin123")
        print("  4. Test the authentication system")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        print("Please check your configuration and try again.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 