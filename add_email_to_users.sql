-- Migration: Add email column to users table
-- Date: 2024
-- Description: Add optional email field for OCTO payment user_data

-- Add email column (nullable for backward compatibility)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE NULL;

-- Add index for efficient email lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Verify migration
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'users' 
AND column_name = 'email';
