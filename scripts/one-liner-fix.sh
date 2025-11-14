#!/bin/bash
# ONE-LINER FIX for PostgreSQL sequence sync
# Copy and paste this entire command on your production server

export PGPASSWORD=$(grep DATABASE_URL ~/.bashrc /etc/environment .env 2>/dev/null | grep -oP 'postgresql.*://[^:]+:\K[^@]+' | head -1) && \
psql -U ubuntu -d slippers <<'EOF'
DO $$ 
DECLARE r RECORD; max_id BIGINT; 
BEGIN 
  FOR r IN SELECT t.table_name, c.column_name, pg_get_serial_sequence(quote_ident(t.table_name), quote_ident(c.column_name)) as seq 
    FROM information_schema.tables t 
    JOIN information_schema.columns c ON t.table_name = c.table_name 
    WHERE t.table_schema = 'public' AND c.column_default LIKE 'nextval%' AND t.table_type = 'BASE TABLE'
  LOOP 
    IF r.seq IS NOT NULL THEN 
      EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I', r.column_name, r.table_name) INTO max_id;
      EXECUTE format('SELECT setval(%L, GREATEST(%s, 1), true)', r.seq, max_id);
      RAISE NOTICE 'Fixed %.%: next ID will be %', r.table_name, r.column_name, max_id + 1;
    END IF; 
  END LOOP; 
END; 
$$;
EOF
unset PGPASSWORD && \
echo "✅ Sequences fixed! Now restart: sudo systemctl restart slippers"
