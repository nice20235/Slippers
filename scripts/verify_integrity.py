#!/usr/bin/env python3
"""
Verify integrity between SQLite and PostgreSQL databases.

Compares row counts and computes an MD5 checksum over rows for each table.

Usage:
  python3 scripts/verify_integrity.py --sqlite ./slippers.db --pg "dbname=mydb user=me password=pass host=127.0.0.1"
"""
import argparse
import sqlite3
import psycopg2
import hashlib
import json
import os
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def row_md5(row):
    # row is a sequence of values; produce stable text representation
    parts = []
    for v in row:
        if v is None:
            parts.append("<NULL>")
        else:
            parts.append(str(v))
    s = "|".join(parts)
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def get_pg_column_types(conn, table: str):
    types = {}
    cur = conn.cursor()
    cur.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
        """,
        (table,)
    )
    for name, dtype in cur.fetchall():
        types[name] = dtype
    return types


def normalize_val(val, pg_type: str):
    if val is None:
        return None
    t = (pg_type or '').lower()
    if t == 'boolean':
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        if s in ('1', 't', 'true', 'y', 'yes'):
            return True
        if s in ('0', 'f', 'false', 'n', 'no'):
            return False
        return False
    if t in ('numeric', 'decimal'):
        try:
            d = Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            # return a fixed representation to ensure identical hashing
            return f"{d:.2f}"
        except (InvalidOperation, ValueError, TypeError):
            return str(val)
    return val


def table_md5_sqlite(conn, table, pk_cols, pg_types, batch=1000):
    cur = conn.cursor()
    order_by = ",".join([f'"{c}"' for c in pk_cols]) if pk_cols else "ROWID"
    cur2 = conn.cursor()
    cur2.execute(f"SELECT COUNT(*) FROM '{table}'")
    total = cur2.fetchone()[0]
    cur.execute(f"SELECT * FROM '{table}' ORDER BY {order_by}")
    md = hashlib.md5()
    processed = 0
    while True:
        rows = cur.fetchmany(batch)
        if not rows:
            break
        for r in rows:
            norm = [normalize_val(r[idx], pg_types.get(cur.description[idx][0])) for idx in range(len(r))]
            md.update(row_md5(norm).encode("ascii"))
        processed += len(rows)
    return total, md.hexdigest()


def table_md5_pg(conn, table, pk_cols, pg_types, batch=1000):
    cur = conn.cursor()
    order_by = ",".join([f'"{c}"' for c in pk_cols]) if pk_cols else "ctid"
    cur.execute(f"SELECT COUNT(*) FROM \"{table}\"")
    total = cur.fetchone()[0]
    cur.execute(f"SELECT * FROM \"{table}\" ORDER BY {order_by}")
    md = hashlib.md5()
    processed = 0
    while True:
        rows = cur.fetchmany(batch)
        if not rows:
            break
        for r in rows:
            norm = [normalize_val(r[idx], pg_types.get(cur.description[idx][0])) for idx in range(len(r))]
            md.update(row_md5(norm).encode("ascii"))
        processed += len(rows)
    return total, md.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Verify SQLite -> Postgres integrity")
    parser.add_argument("--sqlite", default="./slippers.db")
    parser.add_argument("--pg", required=True)
    args = parser.parse_args()

    if not Path(args.sqlite).exists():
        raise SystemExit("SQLite DB not found: %s" % args.sqlite)

    sconn = sqlite3.connect(args.sqlite)
    sconn.row_factory = sqlite3.Row
    pconn = psycopg2.connect(args.pg)

    scur = sconn.cursor()
    scur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = [r[0] for r in scur.fetchall()]

    report = {}
    for t in tables:
        # get pk columns
        scur.execute(f"PRAGMA table_info('{t}')")
        cols = scur.fetchall()
        pk_cols = [c[1] for c in cols if c[5]]
        pg_types = get_pg_column_types(pconn, t)
        print(f"Checking table {t}...", end=" ")
        try:
            s_count, s_md5 = table_md5_sqlite(sconn, t, pk_cols, pg_types)
        except Exception as e:
            s_count, s_md5 = None, None
        try:
            p_count, p_md5 = table_md5_pg(pconn, t, pk_cols, pg_types)
        except Exception as e:
            p_count, p_md5 = None, None

        ok = (s_count == p_count) and (s_md5 == p_md5)
        report[t] = {"sqlite_count": s_count, "sqlite_md5": s_md5, "pg_count": p_count, "pg_md5": p_md5, "match": ok}
        print("done", "MATCH" if ok else "MISMATCH")

    out = os.path.join("scripts", "analysis", "verify_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("Report written to", out)


if __name__ == "__main__":
    main()
