-- Fix missing orders.status column in production database
-- Run this with: psql -h localhost -U slipper_user -d slippers -f fix_orders_schema.sql

BEGIN;

-- Add status column if missing
ALTER TABLE orders ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'PENDING' NOT NULL;

-- Create enum type if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        CREATE TYPE orderstatus AS ENUM ('PENDING', 'PAID', 'REFUNDED');
    END IF;
END$$;

-- Convert column to enum type
ALTER TABLE orders ALTER COLUMN status TYPE orderstatus USING status::orderstatus;

-- Create index if missing
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Verify the fix
SELECT 
    column_name, 
    data_type, 
    udt_name,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'orders' AND column_name = 'status';

COMMIT;

-- Success message
\echo '✅ Orders table schema fixed! Status column added with enum type.'
