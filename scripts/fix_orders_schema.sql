-- Fix missing orders.status column in production database
-- Run this with: psql -h localhost -U slipper_user -d slippers -f fix_orders_schema.sql

BEGIN;

-- Create enum type first if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        CREATE TYPE orderstatus AS ENUM ('PENDING', 'PAID', 'REFUNDED');
    END IF;
END$$;

-- Check if status column exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'orders' AND column_name = 'status'
    ) THEN
        -- Column doesn't exist, add it with enum type
        ALTER TABLE orders ADD COLUMN status orderstatus DEFAULT 'PENDING'::orderstatus NOT NULL;
    ELSE
        -- Column exists, check if it's the right type
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'orders' 
            AND column_name = 'status' 
            AND udt_name != 'orderstatus'
        ) THEN
            -- Drop default first
            ALTER TABLE orders ALTER COLUMN status DROP DEFAULT;
            -- Convert to enum type
            ALTER TABLE orders ALTER COLUMN status TYPE orderstatus 
                USING CASE 
                    WHEN UPPER(status) = 'PENDING' THEN 'PENDING'::orderstatus
                    WHEN UPPER(status) = 'PAID' THEN 'PAID'::orderstatus
                    WHEN UPPER(status) = 'REFUNDED' THEN 'REFUNDED'::orderstatus
                    ELSE 'PENDING'::orderstatus
                END;
            -- Set default back
            ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'PENDING'::orderstatus;
        END IF;
    END IF;
END$$;

-- Create index if missing
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Verify the fix
\echo '📊 Current orders.status column info:'
SELECT 
    column_name, 
    data_type, 
    udt_name,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'orders' AND column_name = 'status';

COMMIT;

\echo '✅ Orders table schema fixed! Status column is now orderstatus enum type.'
