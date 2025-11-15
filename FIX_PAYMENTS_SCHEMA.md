# URGENT: Fix Payments Table Schema

## Issue
Production error: `column "status" of relation "payments" does not exist`

The payments table is missing the `status` column, causing all payment creation requests to fail with 500 errors.

## Solution
Run the migration script to add the missing `status` column with `paymentstatus` enum type.

## Steps to Apply Fix

### 1. Connect to Production Server
```bash
ssh ubuntu@ip-172-31-26-54
```

### 2. Navigate to Project Directory
```bash
cd ~/Slippers
```

### 3. Pull Latest Code
```bash
git pull origin main
```

### 4. Run Migration Script
```bash
psql -U slipper_user -d slippers -f scripts/fix_payments_schema.sql
```

**Expected Output:**
```
psql:scripts/fix_payments_schema.sql:XX: NOTICE:  Created paymentstatus enum type
psql:scripts/fix_payments_schema.sql:XX: NOTICE:  Added status column to payments table with indexes
```

### 5. Verify the Fix
```bash
psql -U slipper_user -d slippers -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'payments' ORDER BY ordinal_position;"
```

You should see the `status` column with type `USER-DEFINED` (paymentstatus enum).

### 6. Restart the Service
```bash
sudo systemctl restart slippers
```

### 7. Check Service Status
```bash
sudo systemctl status slippers
```

### 8. Monitor Logs
```bash
sudo journalctl -u slippers -f
```

Watch for successful payment creation requests without errors.

## Verification

Test the payment endpoint:
1. Create an order from cart: `POST /orders/from-cart`
2. Create payment: `POST /payments/octo/create`
3. Should return 200 OK with payment URL instead of 500 error

## Rollback (if needed)

If something goes wrong:
```sql
psql -U slipper_user -d slippers
ALTER TABLE payments DROP COLUMN IF EXISTS status;
DROP TYPE IF EXISTS paymentstatus CASCADE;
```

## Notes

- This fix is idempotent - safe to run multiple times
- The script checks for existing columns/types before creating them
- Default value is 'CREATED' for all new payments
- Indexes are created for performance: `idx_payments_status` and `idx_payments_order_status`
