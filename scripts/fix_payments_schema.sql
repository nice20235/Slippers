-- Fix payments table schema: add missing status column
-- Run this on production database

\c slippers

-- Create PaymentStatus enum type if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'paymentstatus') THEN
        CREATE TYPE paymentstatus AS ENUM ('CREATED', 'PENDING', 'PAID', 'FAILED', 'CANCELLED', 'REFUNDED');
        RAISE NOTICE 'Created paymentstatus enum type';
    ELSE
        RAISE NOTICE 'paymentstatus enum type already exists';
    END IF;
END$$;

-- Add status column to payments table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'payments' 
        AND column_name = 'status'
    ) THEN
        -- Add the status column with default value
        ALTER TABLE payments 
        ADD COLUMN status paymentstatus NOT NULL DEFAULT 'CREATED'::paymentstatus;
        
        -- Create index on status column
        CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
        
        -- Create composite index on order_id and status (if not exists)
        CREATE INDEX IF NOT EXISTS idx_payments_order_status ON payments(order_id, status);
        
        RAISE NOTICE 'Added status column to payments table with indexes';
    ELSE
        RAISE NOTICE 'status column already exists in payments table';
    END IF;
END$$;

-- Verify the change
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'payments'
ORDER BY ordinal_position;
