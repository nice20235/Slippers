#!/bin/bash
# EMERGENCY FIX - Run this on production server NOW
# Fixes duplicate key errors by resetting all PostgreSQL sequences

echo "🚨 EMERGENCY SEQUENCE FIX"
echo "========================="

# Get database credentials from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Extract DB connection details
if [ -n "$DATABASE_URL" ]; then
    echo "✅ Found DATABASE_URL"
    
    # Extract components from postgresql://user:pass@host/dbname
    DB_USER=$(echo $DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    DB_PASS=$(echo $DATABASE_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^\/]*\)\/.*/\1/p')
    DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
    
    echo "📊 Database: $DB_NAME"
    echo "👤 User: $DB_USER"
    echo "🖥️  Host: $DB_HOST"
    echo ""
else
    echo "❌ DATABASE_URL not found in .env"
    exit 1
fi

# Set password for psql
export PGPASSWORD="$DB_PASS"

echo "🔧 Resetting sequences..."
echo ""

# Run the fix
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" <<'EOSQL'
DO $$ 
DECLARE 
    r RECORD; 
    max_id BIGINT; 
    seq_name TEXT;
BEGIN 
    RAISE NOTICE '🔄 Starting sequence reset...';
    RAISE NOTICE '';
    
    FOR r IN 
        SELECT 
            t.table_name, 
            c.column_name, 
            pg_get_serial_sequence(quote_ident(t.table_name), quote_ident(c.column_name)) as seq 
        FROM information_schema.tables t 
        JOIN information_schema.columns c ON t.table_name = c.table_name 
        WHERE t.table_schema = 'public' 
            AND c.column_default LIKE 'nextval%' 
            AND t.table_type = 'BASE TABLE'
        ORDER BY t.table_name
    LOOP 
        IF r.seq IS NOT NULL THEN 
            -- Get max ID from table
            EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I', r.column_name, r.table_name) INTO max_id;
            
            -- Reset sequence to max_id (next insert will use max_id + 1)
            EXECUTE format('SELECT setval(%L, GREATEST(%s, 1), true)', r.seq, max_id);
            
            RAISE NOTICE '✅ %-20s %-15s: max_id=% next=%', 
                r.table_name, r.column_name, max_id, max_id + 1;
        END IF; 
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE '✅ All sequences reset successfully!';
END; 
$$;
EOSQL

RESULT=$?

# Clear password
unset PGPASSWORD

if [ $RESULT -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Sequences have been reset."
    echo ""
    echo "🎯 Next steps:"
    echo "   1. Restart your service: sudo systemctl restart slippers"
    echo "   2. Test creating a new slipper - should work now!"
    echo ""
    exit 0
else
    echo ""
    echo "❌ FAILED! Check the error above."
    echo ""
    echo "Manual fix (run in psql):"
    echo "  SELECT setval('slippers_id_seq', (SELECT MAX(id) FROM slippers));"
    echo "  SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));"
    echo "  SELECT setval('orders_id_seq', (SELECT MAX(id) FROM orders));"
    echo ""
    exit 1
fi
