# 🚨 EMERGENCY FIX - Duplicate Key Error

## The Error You're Seeing
```
sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint "slippers_pkey"
DETAIL: Key (id)=(14) already exists.
```

## ⚡ INSTANT FIX (Copy-paste on production)

### Option 1: One-Line Command (FASTEST)

```bash
cd ~/Slippers && source venv/bin/activate && ./scripts/EMERGENCY_FIX.sh && sudo systemctl restart slippers
```

### Option 2: Direct SQL (If script fails)

```bash
# Connect to database
psql -U ubuntu -d slippers

# Copy-paste this entire block:
DO $$ 
DECLARE r RECORD; max_id BIGINT; 
BEGIN 
  FOR r IN 
    SELECT t.table_name, c.column_name, 
           pg_get_serial_sequence(quote_ident(t.table_name), quote_ident(c.column_name)) as seq 
    FROM information_schema.tables t 
    JOIN information_schema.columns c ON t.table_name = c.table_name 
    WHERE t.table_schema = 'public' AND c.column_default LIKE 'nextval%' 
  LOOP 
    IF r.seq IS NOT NULL THEN 
      EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I', r.column_name, r.table_name) INTO max_id;
      EXECUTE format('SELECT setval(%L, GREATEST(%s, 1), true)', r.seq, max_id);
      RAISE NOTICE 'Fixed %: next ID = %', r.table_name, max_id + 1;
    END IF; 
  END LOOP; 
END; 
$$;

# Exit psql
\q

# Restart service
sudo systemctl restart slippers
```

### Option 3: Manual Table-by-Table (Ultra-safe)

```bash
psql -U ubuntu -d slippers

# Run each command separately:
SELECT setval('slippers_id_seq', (SELECT COALESCE(MAX(id), 1) FROM slippers), true);
SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users), true);
SELECT setval('orders_id_seq', (SELECT COALESCE(MAX(id), 1) FROM orders), true);
SELECT setval('categories_id_seq', (SELECT COALESCE(MAX(id), 1) FROM categories), true);
SELECT setval('payments_id_seq', (SELECT COALESCE(MAX(id), 1) FROM payments), true);
SELECT setval('carts_id_seq', (SELECT COALESCE(MAX(id), 1) FROM carts), true);
SELECT setval('cart_items_id_seq', (SELECT COALESCE(MAX(id), 1) FROM cart_items), true);
SELECT setval('order_items_id_seq', (SELECT COALESCE(MAX(id), 1) FROM order_items), true);
SELECT setval('slipper_images_id_seq', (SELECT COALESCE(MAX(id), 1) FROM slipper_images), true);

\q
sudo systemctl restart slippers
```

## ✅ Verify It's Fixed

```bash
# Check the slippers sequence
psql -U ubuntu -d slippers -c "SELECT last_value FROM slippers_id_seq;"

# Should return a number >= 14

# Check max slipper ID
psql -U ubuntu -d slippers -c "SELECT MAX(id) FROM slippers;"

# Sequence should be >= max_id
```

## 🎯 Test It Works

```bash
# Try to create a slipper (should work without error)
curl -X POST "http://localhost:8000/slippers/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Slipper","size":"42","price":10.0,"quantity":5,"image":"test.jpg"}'

# Should return 200 OK with created slipper
```

## 🤔 Why This Happens

When you migrated from SQLite to PostgreSQL:
1. **Table data copied**: slippers with IDs 1, 2, 3, ..., 14
2. **Sequences not updated**: `slippers_id_seq` still at default (1 or lower)
3. **Next insert tries ID 14**: But ID 14 already exists → **ERROR**

The fix sets the sequence to MAX(id), so next insert uses MAX(id) + 1.

## 📋 What Each Option Does

| Option | Speed | Safety | When to Use |
|--------|-------|--------|-------------|
| Script | ⚡⚡⚡ | ✅✅✅ | Preferred - automated |
| SQL Block | ⚡⚡ | ✅✅✅ | If script fails |
| Manual | ⚡ | ✅✅✅ | Maximum control |

All options are **100% safe** - they only update sequence counters, never modify data.

## 🆘 Still Not Working?

1. **Check you ran the command as correct user:**
   ```bash
   whoami  # Should be ubuntu or postgres
   ```

2. **Check database connection:**
   ```bash
   psql -U ubuntu -d slippers -c "SELECT 1;"
   ```

3. **Check sequence permissions:**
   ```sql
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ubuntu;
   ```

4. **Manual nuclear option (resets to current max):**
   ```bash
   for seq in $(psql -U ubuntu -d slippers -t -c "SELECT sequencename FROM pg_sequences WHERE schemaname='public'"); do
       table=$(echo $seq | sed 's/_id_seq$//')
       psql -U ubuntu -d slippers -c "SELECT setval('$seq', (SELECT COALESCE(MAX(id), 1) FROM $table), true);"
   done
   ```

---

**This MUST be run on your production server, not locally!**

After running any option above, the error will be **permanently fixed**. ✅
