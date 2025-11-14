#!/bin/bash
# Quick fix for PostgreSQL sequence sync issues
# Usage: ./scripts/quick_fix_sequences.sh

echo "🔧 Quick PostgreSQL Sequence Fix"
echo "=================================="
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not set. Checking .env file..."
    if [ -f .env ]; then
        export $(cat .env | grep DATABASE_URL | xargs)
    fi
fi

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL not found in environment or .env"
    echo "Please set it like: export DATABASE_URL=postgresql://user:pass@host/dbname"
    exit 1
fi

# Extract connection details from DATABASE_URL
if [[ $DATABASE_URL =~ postgresql(\+asyncpg)?://([^:]+):([^@]+)@([^/]+)/(.+) ]]; then
    DB_USER="${BASH_REMATCH[2]}"
    DB_PASS="${BASH_REMATCH[3]}"
    DB_HOST_PORT="${BASH_REMATCH[4]}"
    DB_NAME="${BASH_REMATCH[5]}"
    
    # Remove any query parameters from DB_NAME
    DB_NAME="${DB_NAME%%\?*}"
    
    echo "📊 Database: $DB_NAME"
    echo "👤 User: $DB_USER"
    echo "🖥️  Host: $DB_HOST_PORT"
    echo ""
else
    echo "❌ Error: Could not parse DATABASE_URL"
    exit 1
fi

# Set PGPASSWORD for psql
export PGPASSWORD="$DB_PASS"

# SQL to reset all sequences
SQL="
DO \$\$
DECLARE
    r RECORD;
    max_id BIGINT;
    seq_name TEXT;
BEGIN
    FOR r IN 
        SELECT 
            t.table_name,
            c.column_name,
            pg_get_serial_sequence(quote_ident(t.table_name), quote_ident(c.column_name)) as sequence_name
        FROM information_schema.tables t
        JOIN information_schema.columns c ON t.table_name = c.table_name
        WHERE t.table_schema = 'public'
            AND c.column_default LIKE 'nextval%'
            AND t.table_type = 'BASE TABLE'
    LOOP
        IF r.sequence_name IS NOT NULL THEN
            -- Get max ID
            EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I', r.column_name, r.table_name) INTO max_id;
            
            -- Reset sequence to max_id (next insert will use max_id + 1)
            EXECUTE format('SELECT setval(%L, %s, true)', r.sequence_name, max_id);
            
            RAISE NOTICE '✅ Reset %.% sequence to % (next: %)', r.table_name, r.column_name, max_id, max_id + 1;
        END IF;
    END LOOP;
END;
\$\$;
"

echo "🔄 Resetting sequences..."
echo ""

# Run the SQL
if psql -h "$DB_HOST_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$SQL" 2>&1 | grep -E "(✅|ERROR|NOTICE)"; then
    echo ""
    echo "✅ Sequences reset successfully!"
    echo ""
    echo "🎯 Next steps:"
    echo "   1. Restart your application: sudo systemctl restart slippers"
    echo "   2. Test creating a new record"
else
    echo "❌ Failed to reset sequences"
    exit 1
fi

# Unset password
unset PGPASSWORD
