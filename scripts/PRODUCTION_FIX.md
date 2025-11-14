# 🚨 PRODUCTION FIX: Sequence Synchronization

## Problem
```
sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint "slippers_pkey"
DETAIL: Key (id)=(10) already exists.
```

This happens when PostgreSQL sequences are out of sync with the actual data after migration from SQLite.

## ⚡ Quick Fix (Choose ONE method)

### Method 1: SQL Script (Fastest - Recommended)
```bash
# On production server
cd ~/Slippers
source venv/bin/activate

# Get your database credentials from .env
cat .env | grep DATABASE_URL

# Run the fix script
psql -U ubuntu -d slippers -f scripts/fix_sequences.sql

# Restart application
sudo systemctl restart slippers
```

### Method 2: Bash Script (Automatic)
```bash
cd ~/Slippers
source venv/bin/activate

# Make script executable
chmod +x scripts/quick_fix_sequences.sh

# Run it (reads DATABASE_URL from .env automatically)
./scripts/quick_fix_sequences.sh

# Restart application
sudo systemctl restart slippers
```

### Method 3: Python Script (Most Detailed Output)
```bash
cd ~/Slippers
source venv/bin/activate

# Using DATABASE_URL from environment
python scripts/reset_sequences.py

# OR with explicit connection
python scripts/reset_sequences.py --pg "dbname=slippers user=ubuntu password=YOUR_PASS host=localhost"

# Restart application
sudo systemctl restart slippers
```

### Method 4: Manual SQL (If scripts don't work)
```bash
# Connect to PostgreSQL
psql -U ubuntu -d slippers

# Run these commands one by one:
SELECT setval('slippers_id_seq', (SELECT COALESCE(MAX(id), 1) FROM slippers), true);
SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users), true);
SELECT setval('orders_id_seq', (SELECT COALESCE(MAX(id), 1) FROM orders), true);
SELECT setval('categories_id_seq', (SELECT COALESCE(MAX(id), 1) FROM categories), true);
SELECT setval('payments_id_seq', (SELECT COALESCE(MAX(id), 1) FROM payments), true);
SELECT setval('carts_id_seq', (SELECT COALESCE(MAX(id), 1) FROM carts), true);
SELECT setval('cart_items_id_seq', (SELECT COALESCE(MAX(id), 1) FROM cart_items), true);
SELECT setval('order_items_id_seq', (SELECT COALESCE(MAX(id), 1) FROM order_items), true);
SELECT setval('slipper_images_id_seq', (SELECT COALESCE(MAX(id), 1) FROM slipper_images), true);

-- Exit
\q
```

Then restart:
```bash
sudo systemctl restart slippers
```

## ✅ Verify the Fix

```bash
# Check a specific sequence
psql -U ubuntu -d slippers -c "SELECT last_value FROM slippers_id_seq;"
# Should show a number >= your max slipper ID

# Check all sequences
psql -U ubuntu -d slippers -c "
SELECT 
    schemaname, 
    sequencename, 
    last_value 
FROM pg_sequences 
WHERE schemaname = 'public' 
ORDER BY sequencename;
"
```

## 🎯 Test It Works

After restarting, try creating a slipper through your API:
```bash
curl -X POST "https://your-domain.com/slippers/" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Slipper",
    "size": "42",
    "price": 19.99,
    "quantity": 10,
    "image": "test.jpg"
  }'
```

Should return 200 OK with the created slipper (no more duplicate key errors!).

## 📚 What Each Method Does

All methods do the same thing:
1. Find all auto-increment sequences in your database
2. Check the MAX(id) for each table
3. Set the sequence to MAX(id), so next insert uses MAX(id) + 1
4. This prevents trying to reuse existing IDs

## 🔍 Root Cause

SQLite uses implicit auto-increment without explicit sequences. When data is migrated to PostgreSQL:
- Table rows are copied with their original IDs (1, 2, 3, ..., 10)
- PostgreSQL sequences remain at default starting value (1)
- Next insert asks sequence for next ID → gets 1, but 1 already exists → **ERROR**

## 🛡️ Prevention

The auto-migration in `app/db/init_db.py` now includes automatic sequence reset, but for manually migrated databases, you need to run one of these scripts once.

## ⚠️ Important Notes

- Run this **after** migration is complete
- Safe to run multiple times (idempotent)
- No data is lost or modified
- Only sequence counters are updated
- Application must be restarted after running

## 🆘 Still Having Issues?

If you still see duplicate key errors after running the fix:

1. **Check if fix actually ran**:
   ```bash
   psql -U ubuntu -d slippers -c "SELECT last_value FROM slippers_id_seq;"
   ```

2. **Check max ID in table**:
   ```bash
   psql -U ubuntu -d slippers -c "SELECT MAX(id) FROM slippers;"
   ```

3. **Sequence should be >= max ID**. If not, there might be a permissions issue.

4. **Check PostgreSQL logs**:
   ```bash
   sudo tail -f /var/log/postgresql/postgresql-*.log
   ```

5. **Verify user has sequence permissions**:
   ```sql
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ubuntu;
   ```
