# 🚨 URGENT: Production Schema Fix + Deployment

## Critical Issue Found

Your production database is **missing the `status` column** in the `orders` table. This is causing 500 errors on `/orders/` endpoint.

## Quick Fix (Run on Production Server)

### Option 1: One-Command Fix (Fastest)

```bash
cd ~/Slippers && \
git pull origin main && \
psql -h localhost -U slipper_user -d slippers -f scripts/fix_orders_schema.sql && \
sudo systemctl restart slippers && \
echo "✅ Schema fixed and service restarted!"
```

### Option 2: Step-by-Step Fix

```bash
# 1. Pull latest code (includes schema fix script)
cd ~/Slippers
git pull origin main

# 2. Apply schema fix
psql -h localhost -U slipper_user -d slippers -f scripts/fix_orders_schema.sql

# 3. Restart service
sudo systemctl restart slippers

# 4. Check logs
sudo journalctl -u slippers -n 20 --no-pager
```

### Option 3: Manual SQL Fix

```bash
# Connect to database
psql -h localhost -U slipper_user -d slippers

# Run these commands:
```sql
BEGIN;

ALTER TABLE orders ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'PENDING' NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        CREATE TYPE orderstatus AS ENUM ('PENDING', 'PAID', 'REFUNDED');
    END IF;
END$$;

ALTER TABLE orders ALTER COLUMN status TYPE orderstatus USING status::orderstatus;
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

COMMIT;
```

Exit with `\q` then restart: `sudo systemctl restart slippers`

## Verification

After fixing, test the endpoint:

```bash
# Should return 200 OK (not 500 error)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/orders/

# Should show order data
curl http://localhost:8000/orders/ | head -n 20
```

## What Caused This

The production database schema was never updated after you added the `status` column to your `Order` model. The code expects `orders.status` but the database doesn't have it.

## After Fix - Deploy Optimizations

Once the schema is fixed, deploy all optimizations:

```bash
cd ~/Slippers
git pull origin main
source venv/bin/activate  # or your virtualenv path
pip install -r requirements.txt --upgrade
cd scripts
./EMERGENCY_FIX.sh  # Fix sequence issues
cd ..
sudo systemctl restart slippers
```

## Expected Result

✅ **Before Fix:**
```
ERROR: column orders.status does not exist
500 Internal Server Error
```

✅ **After Fix:**
```
200 OK
Orders endpoint working correctly
```

## Check Service Status

```bash
# Check if running
sudo systemctl status slippers

# Watch logs in real-time
sudo journalctl -u slippers -f

# Check recent errors
sudo journalctl -u slippers -p err --since "10 minutes ago"
```

## Rollback Plan

If something goes wrong:

```bash
# Rollback schema change
psql -h localhost -U slipper_user -d slippers -c "ALTER TABLE orders DROP COLUMN IF EXISTS status CASCADE;"

# Restart service
sudo systemctl restart slippers
```

---

**⚠️ RUN THE FIX NOW TO RESOLVE 500 ERRORS!**
