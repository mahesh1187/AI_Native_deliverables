"""
Snowflake Connection Utility
=============================
Connects to Snowflake using credentials from a .env file.
Provides helper functions for querying and loading data.

Usage:
    1. Fill in your credentials in the .env file
    2. Run this script:  python snowflake_connect.py
"""

import os
import sys
import snowflake.connector
from dotenv import load_dotenv

# Fix Windows console encoding for emoji/unicode output
sys.stdout.reconfigure(encoding='utf-8')


# ─── Load environment variables ────────────────────────────────────────────────
load_dotenv()

SNOWFLAKE_CONFIG = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
    "user":      os.getenv("SNOWFLAKE_USER"),
    "password":  os.getenv("SNOWFLAKE_PASSWORD"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database":  os.getenv("SNOWFLAKE_DATABASE"),
    "schema":    os.getenv("SNOWFLAKE_SCHEMA"),
    "role":      os.getenv("SNOWFLAKE_ROLE"),
}


def get_connection():
    """Create and return a Snowflake connection using .env credentials."""
    # Remove keys with None values so Snowflake doesn't choke on them
    config = {k: v for k, v in SNOWFLAKE_CONFIG.items() if v and v != f"your_{k}"}

    if "account" not in config or "user" not in config or "password" not in config:
        print("❌ Missing required credentials in .env file.")
        print("   Please set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, and SNOWFLAKE_PASSWORD")
        sys.exit(1)

    try:
        conn = snowflake.connector.connect(**config)
        print("✅ Successfully connected to Snowflake!")
        return conn
    except snowflake.connector.errors.DatabaseError as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)


def run_query(conn, query):
    """Execute a query and return the results as a list of dicts."""
    cursor = conn.cursor(snowflake.connector.DictCursor)
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    finally:
        cursor.close()


def show_account_info(conn):
    """Print basic account information to verify the connection."""
    print("\n" + "=" * 60)
    print("  SNOWFLAKE CONNECTION INFO")
    print("=" * 60)

    # Current user & role
    result = run_query(conn, "SELECT CURRENT_USER() AS user, CURRENT_ROLE() AS role")
    if result:
        print(f"  👤 User:      {result[0]['USER']}")
        print(f"  🎭 Role:      {result[0]['ROLE']}")

    # Current warehouse, database, schema
    result = run_query(conn, """
        SELECT CURRENT_WAREHOUSE() AS warehouse,
               CURRENT_DATABASE()  AS database,
               CURRENT_SCHEMA()    AS schema
    """)
    if result:
        print(f"  🏭 Warehouse: {result[0]['WAREHOUSE']}")
        print(f"  🗄️  Database:  {result[0]['DATABASE']}")
        print(f"  📁 Schema:    {result[0]['SCHEMA']}")

    # Snowflake version
    result = run_query(conn, "SELECT CURRENT_VERSION() AS version")
    if result:
        print(f"  ❄️  Version:   {result[0]['VERSION']}")

    print("=" * 60)


def list_databases(conn):
    """List all accessible databases."""
    print("\n📦 Accessible Databases:")
    results = run_query(conn, "SHOW DATABASES")
    for row in results:
        print(f"   • {row['name']}")


def list_schemas(conn, database=None):
    """List all schemas in the current or specified database."""
    db = database or SNOWFLAKE_CONFIG.get("database")
    if db:
        print(f"\n📂 Schemas in '{db}':")
        results = run_query(conn, f"SHOW SCHEMAS IN DATABASE {db}")
        for row in results:
            print(f"   • {row['name']}")
    else:
        print("⚠️  No database specified. Set SNOWFLAKE_DATABASE in .env or pass a database name.")


def list_tables(conn, database=None, schema=None):
    """List all tables in the current or specified database/schema."""
    db = database or SNOWFLAKE_CONFIG.get("database")
    sc = schema or SNOWFLAKE_CONFIG.get("schema")
    if db and sc:
        print(f"\n📋 Tables in '{db}.{sc}':")
        results = run_query(conn, f"SHOW TABLES IN {db}.{sc}")
        for row in results:
            print(f"   • {row['name']}  ({row['rows']} rows)")
    else:
        print("⚠️  Database and schema required. Set them in .env or pass as arguments.")


# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    conn = get_connection()

    try:
        show_account_info(conn)
        list_databases(conn)

        # Uncomment below to explore schemas and tables:
        # list_schemas(conn)
        # list_tables(conn)

        # Run a custom query:
        # results = run_query(conn, "SELECT * FROM your_table LIMIT 10")
        # for row in results:
        #     print(row)

    finally:
        conn.close()
        print("\n🔒 Connection closed.")
