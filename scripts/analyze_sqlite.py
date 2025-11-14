#!/usr/bin/env python3
"""
Analyze a local SQLite database and emit schema and counts.

Outputs:
 - analysis/<timestamp>_sqlite_analysis.json
 - migrations/pg_schema.sql (best-effort conversion)

Run: python3 scripts/analyze_sqlite.py --db ./slippers.db
"""
import argparse
import sqlite3
import json
import os
import datetime
import logging
import re

LOG_DIR = os.path.join("scripts", "logs")
ANALYSIS_DIR = os.path.join("scripts", "analysis")
MIGRATIONS_DIR = os.path.join("migrations")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)
os.makedirs(MIGRATIONS_DIR, exist_ok=True)

logger = logging.getLogger("analyze_sqlite")
handler = logging.FileHandler(os.path.join(LOG_DIR, "analyze.log"))
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


TYPE_MAP = {
    # naive mapping from SQLite affinity/type to PostgreSQL
    "INTEGER": "BIGINT",
    "INT": "BIGINT",
    "TINYINT": "SMALLINT",
    "SMALLINT": "SMALLINT",
    "MEDIUMINT": "INTEGER",
    "BIGINT": "BIGINT",
    "UNSIGNED BIG INT": "BIGINT",
    "REAL": "DOUBLE PRECISION",
    "DOUBLE": "DOUBLE PRECISION",
    "FLOAT": "DOUBLE PRECISION",
    "NUMERIC": "NUMERIC",
    "DECIMAL": "NUMERIC",
    "BOOLEAN": "BOOLEAN",
    "DATE": "DATE",
    "DATETIME": "TIMESTAMP",
    "TIMESTAMP": "TIMESTAMP",
    "TEXT": "TEXT",
    "CHAR": "TEXT",
    "CLOB": "TEXT",
    "BLOB": "BYTEA",
    "JSON": "JSONB",
}


def map_type(sqlite_type: str) -> str:
    if not sqlite_type:
        return "TEXT"
    t = sqlite_type.strip().upper()
    # handle cases like VARCHAR(255)
    m = re.match(r"([A-Z ]+)(\(.+\))?", t)
    base = m.group(1) if m else t
    base = base.strip()
    return TYPE_MAP.get(base, "TEXT")


def analyze(db_path: str):
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_json = os.path.join(ANALYSIS_DIR, f"{ts}_sqlite_analysis.json")
    logger.info("Starting analysis for %s", db_path)

    if not os.path.exists(db_path):
        logger.error("DB file not found: %s", db_path)
        raise SystemExit(f"DB file not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # list tables
    cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    objs = cur.fetchall()

    analysis = {
        "database": os.path.abspath(db_path),
        "generated_at": ts,
        "tables": {},
    }

    # For generating basic pg schema
    pg_ddls = []

    for obj in objs:
        name = obj["name"]
        obj_type = obj["type"]
        sql = obj["sql"]
        logger.info("Inspecting %s %s", obj_type, name)

        table_info = {"type": obj_type, "create_sql": sql, "columns": [], "indexes": [], "foreign_keys": [], "count": 0}

        if obj_type == "table":
            # columns
            cur.execute(f"PRAGMA table_info('{name}');")
            cols = cur.fetchall()
            for c in cols:
                # c: cid, name, type, notnull, dflt_value, pk
                col = {"cid": c[0], "name": c[1], "type": c[2], "notnull": bool(c[3]), "default": c[4], "pk": c[5]}
                table_info["columns"].append(col)

            # indexes
            cur.execute(f"PRAGMA index_list('{name}');")
            idxs = cur.fetchall()
            for idx in idxs:
                # seq, name, unique, origin, partial
                idx_name = idx[1]
                cur.execute(f"PRAGMA index_info('{idx_name}');")
                idx_cols = [r[2] for r in cur.fetchall()]
                table_info["indexes"].append({"name": idx_name, "unique": bool(idx[2]), "columns": idx_cols})

            # foreign keys
            cur.execute(f"PRAGMA foreign_key_list('{name}');")
            fks = cur.fetchall()
            for fk in fks:
                # id, seq, table, from, to, on_update, on_delete, match
                table_info["foreign_keys"].append({"id": fk[0], "seq": fk[1], "table": fk[2], "from": fk[3], "to": fk[4], "on_update": fk[5], "on_delete": fk[6]})

            # row count
            try:
                cur2 = conn.execute(f"SELECT COUNT(*) AS c FROM '{name}';")
                cnt = cur2.fetchone()[0]
            except Exception:
                cnt = -1
            table_info["count"] = cnt

            # Build PG DDL (best-effort)
            cols_ddl = []
            pk_cols = [c["name"] for c in table_info["columns"] if c["pk"]]
            for c in table_info["columns"]:
                colname = c["name"]
                ctype = map_type(c["type"])
                # Force NOT NULL for PK columns for correctness on PG
                notnull_flag = c["notnull"] or c["pk"]
                notnull = " NOT NULL" if notnull_flag else ""
                default = f" DEFAULT {c['default']}" if c["default"] is not None else ""
                cols_ddl.append(f'  "{colname}" {ctype}{notnull}{default}')

            if pk_cols:
                quoted = ", ".join([f'"{p}"' for p in pk_cols])
                pk_stmt = f", PRIMARY KEY ({quoted})"
            else:
                pk_stmt = ""
            create_stmt = f'CREATE TABLE IF NOT EXISTS "{name}" (\n' + ",\n".join(cols_ddl) + pk_stmt + "\n);"
            pg_ddls.append(create_stmt)

        else:
            # views: just copy the SQL
            table_info["create_sql"] = sql

        analysis["tables"][name] = table_info

    # write analysis
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    # write a best-effort pg schema
    pg_file = os.path.join(MIGRATIONS_DIR, "pg_schema.sql")
    with open(pg_file, "w", encoding="utf-8") as f:
        f.write("-- Best-effort generated PostgreSQL schema from SQLite\n")
        f.write("-- Please review before applying to production\n\n")
        for ddl in pg_ddls:
            f.write(ddl + "\n\n")

    logger.info("Analysis complete. JSON: %s  PG schema: %s", out_json, pg_file)
    print("Analysis written to:")
    print(" ", out_json)
    print("Generated best-effort PostgreSQL schema:")
    print(" ", pg_file)


def main():
    parser = argparse.ArgumentParser(description="Analyze SQLite DB and produce a best-effort PostgreSQL schema")
    parser.add_argument("--db", default="./slippers.db", help="Path to SQLite DB file")
    args = parser.parse_args()
    analyze(args.db)


if __name__ == "__main__":
    main()
