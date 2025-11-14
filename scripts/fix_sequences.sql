-- PostgreSQL Sequence Reset Script
-- Fixes "duplicate key value violates unique constraint" errors after SQLite migration
-- 
-- Usage:
--   psql -U ubuntu -d slippers -f scripts/fix_sequences.sql
--   OR
--   psql -U ubuntu -d slippers < scripts/fix_sequences.sql

\echo '========================================='
\echo 'PostgreSQL Sequence Reset Script'
\echo '========================================='
\echo ''

-- Function to reset all sequences
DO $$
DECLARE
    r RECORD;
    max_id BIGINT;
    next_val BIGINT;
    current_val BIGINT;
BEGIN
    RAISE NOTICE 'Starting sequence reset...';
    RAISE NOTICE '';
    
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
        ORDER BY t.table_name
    LOOP
        IF r.sequence_name IS NOT NULL THEN
            -- Get current sequence value
            EXECUTE format('SELECT last_value FROM %s', r.sequence_name) INTO current_val;
            
            -- Get max ID from table
            EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I', r.column_name, r.table_name) INTO max_id;
            
            -- Only update if max_id is greater than or equal to current value
            IF max_id >= current_val THEN
                -- Reset sequence to max_id (using 'true' means last_value = max_id, next will be max_id + 1)
                EXECUTE format('SELECT setval(%L, GREATEST(%s, 1), true)', r.sequence_name, max_id);
                next_val := max_id + 1;
                
                RAISE NOTICE '✅ %-20s %-15s: current=% max_id=% → next=%', 
                    r.table_name, r.column_name, current_val, max_id, next_val;
            ELSE
                RAISE NOTICE '⏭️  %-20s %-15s: current=% max_id=% (no change needed)', 
                    r.table_name, r.column_name, current_val, max_id;
            END IF;
        END IF;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE '✅ All sequences have been reset!';
    RAISE NOTICE '';
    RAISE NOTICE '🎯 Next steps:';
    RAISE NOTICE '   1. Restart your application';
    RAISE NOTICE '   2. Test creating new records';
END;
$$;

\echo ''
\echo '========================================='
\echo 'Verification: Current sequence values'
\echo '========================================='

-- Show current sequence values
SELECT 
    t.table_name,
    c.column_name,
    pg_get_serial_sequence(quote_ident(t.table_name), quote_ident(c.column_name)) as sequence_name,
    (SELECT last_value FROM pg_sequences WHERE schemaname = 'public' AND sequencename = substring(pg_get_serial_sequence(quote_ident(t.table_name), quote_ident(c.column_name)) FROM 'public\.(.*)')) as last_value
FROM information_schema.tables t
JOIN information_schema.columns c ON t.table_name = c.table_name
WHERE t.table_schema = 'public'
    AND c.column_default LIKE 'nextval%'
    AND t.table_type = 'BASE TABLE'
ORDER BY t.table_name;

\echo ''
\echo '✅ Done! Sequences are now synchronized.'
\echo ''
