#!/usr/bin/env python3
"""
Reset PostgreSQL sequences to fix 'duplicate key' errors after migration.

Usage:
    python scripts/reset_sequences.py --pg "dbname=slippers user=myuser password=pass host=localhost"
    
Or set DATABASE_URL environment variable:
    DATABASE_URL=postgresql://user:pass@localhost/slippers python scripts/reset_sequences.py
"""

import sys
import argparse
import os
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 is required. Install with: pip install psycopg2-binary")
    sys.exit(1)


def reset_sequences(dsn: str):
    """Reset all sequences in PostgreSQL database to match max IDs."""
    print(f"Connecting to PostgreSQL...")
    
    try:
        conn = psycopg2.connect(dsn)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Find all sequences
        print("\nFinding sequences...")
        cur.execute("""
            SELECT 
                t.table_name,
                c.column_name,
                pg_get_serial_sequence(quote_ident(t.table_name), quote_ident(c.column_name)) as sequence_name
            FROM information_schema.tables t
            JOIN information_schema.columns c 
                ON t.table_name = c.table_name
            WHERE t.table_schema = 'public'
                AND c.column_default LIKE 'nextval%'
                AND t.table_type = 'BASE TABLE'
        """)
        
        sequences = cur.fetchall()
        
        if not sequences:
            print("No sequences found.")
            return
        
        print(f"Found {len(sequences)} sequences\n")
        
        fixed = 0
        for row in sequences:
            table_name = row['table_name']
            column_name = row['column_name']
            sequence_name = row['sequence_name']
            
            if not sequence_name:
                continue
            
            try:
                # Get current sequence value
                cur.execute(f"SELECT last_value FROM {sequence_name}")
                current_val = cur.fetchone()['last_value']
                
                # Get max ID from table
                cur.execute(f'SELECT MAX("{column_name}") as max_id FROM "{table_name}"')
                max_id = cur.fetchone()['max_id']
                
                if max_id is None:
                    print(f"⚠️  {table_name}.{column_name}: Empty table, skipping")
                    continue
                
                # Reset sequence
                cur.execute(f"SELECT setval('{sequence_name}', %s, true)", (max_id,))
                conn.commit()
                
                status = "✅" if max_id >= current_val else "🔧"
                print(f"{status} {table_name}.{column_name}: {current_val} → {max_id} (sequence: {sequence_name})")
                fixed += 1
                
            except Exception as e:
                print(f"❌ Failed to reset {sequence_name}: {e}")
                conn.rollback()
        
        print(f"\n✅ Successfully reset {fixed}/{len(sequences)} sequences")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Reset PostgreSQL sequences after SQLite migration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using connection string
  python reset_sequences.py --pg "dbname=slippers user=myuser password=pass host=localhost port=5432"
  
  # Using DATABASE_URL environment variable
  DATABASE_URL=postgresql://user:pass@localhost/slippers python reset_sequences.py
  
  # Using individual parameters
  python reset_sequences.py --dbname slippers --user myuser --password pass --host localhost
        """
    )
    
    parser.add_argument('--pg', help='PostgreSQL DSN connection string')
    parser.add_argument('--dbname', help='Database name')
    parser.add_argument('--user', help='Database user')
    parser.add_argument('--password', help='Database password')
    parser.add_argument('--host', default='localhost', help='Database host (default: localhost)')
    parser.add_argument('--port', default='5432', help='Database port (default: 5432)')
    
    args = parser.parse_args()
    
    # Build DSN
    dsn = None
    
    if args.pg:
        dsn = args.pg
    elif args.dbname and args.user:
        dsn_parts = [
            f"dbname={args.dbname}",
            f"user={args.user}",
            f"host={args.host}",
            f"port={args.port}",
        ]
        if args.password:
            dsn_parts.append(f"password={args.password}")
        dsn = " ".join(dsn_parts)
    elif os.getenv('DATABASE_URL'):
        # Convert SQLAlchemy URL to libpq DSN
        db_url = os.getenv('DATABASE_URL')
        if db_url.startswith('postgresql+asyncpg://'):
            db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        if db_url.startswith('postgresql://'):
            # Extract components
            from urllib.parse import urlparse
            parsed = urlparse(db_url)
            dsn_parts = [f"dbname={parsed.path[1:]}"]
            if parsed.username:
                dsn_parts.append(f"user={parsed.username}")
            if parsed.password:
                dsn_parts.append(f"password={parsed.password}")
            if parsed.hostname:
                dsn_parts.append(f"host={parsed.hostname}")
            if parsed.port:
                dsn_parts.append(f"port={parsed.port}")
            dsn = " ".join(dsn_parts)
    
    if not dsn:
        parser.print_help()
        print("\n❌ Error: No database connection specified. Use --pg, --dbname/--user, or DATABASE_URL env var")
        sys.exit(1)
    
    print("=" * 60)
    print("PostgreSQL Sequence Reset Tool")
    print("=" * 60)
    
    reset_sequences(dsn)


if __name__ == '__main__':
    main()
