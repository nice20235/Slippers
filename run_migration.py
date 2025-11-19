"""Run database migration to add email column to users table"""
import asyncio
import asyncpg
from app.core.config import settings


async def run_migration():
    """Execute the email column migration"""
    print("Connecting to database...")
    conn = await asyncpg.connect(settings.DATABASE_URL)
    
    try:
        print("Adding email column to users table...")
        
        # Add email column
        await conn.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE NULL
        """)
        print("✓ Email column added")
        
        # Add index
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
        """)
        print("✓ Index created")
        
        # Verify migration
        result = await conn.fetch("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default
            FROM information_schema.columns
            WHERE table_name = 'users' 
            AND column_name = 'email'
        """)
        
        if result:
            print("\n✅ Migration completed successfully!")
            print("\nEmail column details:")
            for row in result:
                print(f"  Column: {row['column_name']}")
                print(f"  Type: {row['data_type']}")
                print(f"  Nullable: {row['is_nullable']}")
                print(f"  Default: {row['column_default']}")
        else:
            print("❌ Email column not found after migration")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()
        print("\nDatabase connection closed")


if __name__ == "__main__":
    asyncio.run(run_migration())
