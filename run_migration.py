"""Run database migration to add email column to users table"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.db.database import engine
from sqlalchemy import text


async def run_migration():
    """Execute the email column migration"""
    print("🔄 Starting email column migration...")
    print("=" * 50)
    
    try:
        async with engine.begin() as conn:
            print("Adding email column to users table...")
            
            # Add email column
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE NULL
            """))
            print("  ✅ Email column added")
            
            # Add index
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
            """))
            print("  ✅ Index created")
            
            # Verify migration
            result = await conn.execute(text("""
                SELECT 
                    column_name, 
                    data_type, 
                    is_nullable, 
                    column_default
                FROM information_schema.columns
                WHERE table_name = 'users' 
                AND column_name = 'email'
            """))
            
            rows = result.fetchall()
            
            if rows:
                print("\n" + "=" * 50)
                print("✅ Migration completed successfully!")
                print("\nEmail column details:")
                for row in rows:
                    print(f"  Column: {row[0]}")
                    print(f"  Type: {row[1]}")
                    print(f"  Nullable: {row[2]}")
                    print(f"  Default: {row[3]}")
            else:
                print("❌ Email column not found after migration")
                sys.exit(1)
            
        print("\n🎉 Migration finished successfully!")
        print("\n📝 Next steps:")
        print("  1. Restart your application")
        print("  2. Users can now register with email")
        print("  3. OCTO payments will send user_data")
                
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nPlease check your database connection and try again.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_migration())
