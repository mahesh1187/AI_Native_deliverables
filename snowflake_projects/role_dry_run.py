"""
Role Permission Dry Run
=========================
Switches to each custom BANK role and tests:
  1. Which tables the role can SELECT from
  2. How masking policies affect sensitive columns
  3. Whether INSERT/UPDATE/DELETE operations are allowed

Usage:
    python role_dry_run.py
"""

import os
import sys
import snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

# ─── Config ────────────────────────────────────────────────────────────────────

ROLES = [
    "BANK_DB_ADMIN",
    "BANK_DATA_ENGINEER",
    "BANK_DATA_ANALYST",
    "BANK_DATA_SCIENTIST",
    "BANK_APP_SERVICE",
    "BANK_COMPLIANCE_OFFICER",
    "BANK_BRANCH_MANAGER",
    "BANK_LOAN_OFFICER",
    "BANK_TELLER",
    "BANK_CUSTOMER_SERVICE",
    "BANK_READ_ONLY",
]

TABLES = [
    "BRANCHES", "CUSTOMERS", "EMPLOYEES", "ACCOUNTS",
    "TRANSACTIONS", "LOANS", "LOAN_PAYMENTS", "CARDS"
]

# Sensitive columns to check masking
MASKING_CHECKS = {
    "CUSTOMERS": ["CUSTOMER_ID", "FIRST_NAME", "PAN_NUMBER", "AADHAR_NUMBER", "EMAIL"],
    "CARDS": ["CARD_ID", "CARD_NUMBER", "CVV", "CARD_TYPE"],
}

# Write operations to test
WRITE_TESTS = {
    "TRANSACTIONS": {
        "insert": """INSERT INTO BANK.TRANSACTIONS (TRANSACTION_ID, ACCOUNT_ID, TRANSACTION_TYPE, AMOUNT, TRANSACTION_DATE)
                     VALUES (999999, 1, 'Test', 0.01, CURRENT_TIMESTAMP())""",
        "update": "UPDATE BANK.TRANSACTIONS SET DESCRIPTION = 'test' WHERE TRANSACTION_ID = 999999",
        "delete": "DELETE FROM BANK.TRANSACTIONS WHERE TRANSACTION_ID = 999999",
    },
    "LOANS": {
        "insert": """INSERT INTO BANK.LOANS (LOAN_ID, CUSTOMER_ID, LOAN_TYPE, PRINCIPAL_AMOUNT, INTEREST_RATE, TENURE_MONTHS)
                     VALUES (999999, 1, 'Test', 1000, 10, 12)""",
        "update": "UPDATE BANK.LOANS SET STATUS = 'Test' WHERE LOAN_ID = 999999",
        "delete": "DELETE FROM BANK.LOANS WHERE LOAN_ID = 999999",
    },
    "CUSTOMERS": {
        "insert": """INSERT INTO BANK.CUSTOMERS (CUSTOMER_ID, FIRST_NAME, LAST_NAME)
                     VALUES (999999, 'Test', 'User')""",
        "update": "UPDATE BANK.CUSTOMERS SET CITY = 'Test' WHERE CUSTOMER_ID = 999999",
        "delete": "DELETE FROM BANK.CUSTOMERS WHERE CUSTOMER_ID = 999999",
    },
    "ACCOUNTS": {
        "insert": """INSERT INTO BANK.ACCOUNTS (ACCOUNT_ID, ACCOUNT_NUMBER, CUSTOMER_ID, ACCOUNT_TYPE, OPENED_DATE)
                     VALUES (999999, '9999999999', 1, 'Test', CURRENT_DATE())""",
        "update": "UPDATE BANK.ACCOUNTS SET STATUS = 'Test' WHERE ACCOUNT_ID = 999999",
        "delete": "DELETE FROM BANK.ACCOUNTS WHERE ACCOUNT_ID = 999999",
    },
}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def test_select(cursor, table):
    """Test if SELECT is allowed on a table. Returns (allowed, row_count)."""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM BANK.{table}")
        count = cursor.fetchone()[0]
        return True, count
    except Exception:
        return False, 0


def test_write(cursor, operation, sql):
    """Test if a write operation is allowed. Returns True/False."""
    try:
        cursor.execute("BEGIN")
        cursor.execute(sql)
        cursor.execute("ROLLBACK")  # Always rollback — dry run only
        return True
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        return False


def check_masking(cursor, table, columns):
    """Check what a role sees for sensitive columns."""
    col_list = ", ".join(columns)
    try:
        cursor.execute(f"SELECT {col_list} FROM BANK.{table} LIMIT 1")
        row = cursor.fetchone()
        if row:
            return {col: str(val) for col, val in zip(columns, row)}
        return {col: "—" for col in columns}
    except Exception:
        return {col: "❌ NO ACCESS" for col in columns}


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    config = {
        "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
        "user":      os.getenv("SNOWFLAKE_USER"),
        "password":  os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database":  "TEST_BANK",
        "role":      "ACCOUNTADMIN",
    }
    config = {k: v for k, v in config.items() if v}

    print("🔗 Connecting to Snowflake...")
    conn = snowflake.connector.connect(**config)
    cursor = conn.cursor()
    print("✅ Connected!\n")

    try:
        for role in ROLES:
            print("╔" + "═" * 73 + "╗")
            print(f"║  🎭 ROLE: {role:60s}   ║")
            print("╚" + "═" * 73 + "╝")

            # Switch role
            try:
                cursor.execute(f"USE ROLE {role}")
                cursor.execute(f"USE DATABASE TEST_BANK")
                cursor.execute(f"USE WAREHOUSE {os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')}")
            except Exception as e:
                print(f"  ❌ Cannot assume role: {e}\n")
                continue

            # ── 1. Table Access (SELECT) ───────────────────────────────────
            print("\n  ┌─────────────────────────────────────────────────────────┐")
            print("  │  📊 TABLE ACCESS (SELECT)                              │")
            print("  ├──────────────────────────┬─────────┬────────────────────┤")
            print("  │ Table                    │ Access  │ Rows               │")
            print("  ├──────────────────────────┼─────────┼────────────────────┤")

            for table in TABLES:
                allowed, count = test_select(cursor, table)
                access_icon = "✅ Yes" if allowed else "❌ No "
                count_str = f"{count:,}" if allowed else "—"
                print(f"  │ {table:24s} │ {access_icon} │ {count_str:>18s} │")

            print("  └──────────────────────────┴─────────┴────────────────────┘")

            # ── 2. Write Permissions ───────────────────────────────────────
            print("\n  ┌──────────────────────────────────────────────────────────────┐")
            print("  │  ✏️  WRITE PERMISSIONS (DML) — All operations are ROLLED BACK │")
            print("  ├──────────────────────┬──────────┬──────────┬──────────────────┤")
            print("  │ Table                │ INSERT   │ UPDATE   │ DELETE           │")
            print("  ├──────────────────────┼──────────┼──────────┼──────────────────┤")

            for table, ops in WRITE_TESTS.items():
                insert_ok = test_write(cursor, "INSERT", ops["insert"])
                update_ok = test_write(cursor, "UPDATE", ops["update"])
                delete_ok = test_write(cursor, "DELETE", ops["delete"])

                i_icon = "✅ Yes  " if insert_ok else "❌ No   "
                u_icon = "✅ Yes  " if update_ok else "❌ No   "
                d_icon = "✅ Yes        " if delete_ok else "❌ No         "
                print(f"  │ {table:20s} │ {i_icon} │ {u_icon} │ {d_icon} │")

            print("  └──────────────────────┴──────────┴──────────┴──────────────────┘")

            # ── 3. Data Masking ────────────────────────────────────────────
            print("\n  ┌───────────────────────────────────────────────────────────────────┐")
            print("  │  🔒 DATA MASKING (Sensitive Columns — 1 sample row)               │")
            print("  ├───────────────────────────────────────────────────────────────────┤")

            for table, columns in MASKING_CHECKS.items():
                values = check_masking(cursor, table, columns)
                print(f"  │  Table: {table:57s} │")
                for col, val in values.items():
                    # Determine if masked
                    if val in ("**MASKED**", "***") or val.startswith("XXXXX") or val.startswith("XXXX-"):
                        indicator = "🔴 MASKED"
                    elif val == "❌ NO ACCESS":
                        indicator = "⛔ DENIED"
                    elif "***@" in val:
                        indicator = "🟡 PARTIAL"
                    else:
                        indicator = "🟢 VISIBLE"
                    display_val = val[:30] if len(val) > 30 else val
                    print(f"  │    {col:18s} = {display_val:30s} {indicator} │")
                print("  │" + " " * 67 + "│")

            print("  └───────────────────────────────────────────────────────────────────┘")

            # ── 4. Schema Access ───────────────────────────────────────────
            print("\n  ┌─────────────────────────────────────────────────────────┐")
            print("  │  📁 SCHEMA ACCESS                                      │")
            print("  ├──────────────────────────┬──────────────────────────────┤")
            print("  │ Schema                   │ Access                       │")
            print("  ├──────────────────────────┼──────────────────────────────┤")

            for schema in ["BANK", "ANALYTICS", "SANDBOX", "STAGING", "PUBLIC"]:
                try:
                    cursor.execute(f"USE SCHEMA TEST_BANK.{schema}")
                    # Test if can create objects
                    try:
                        cursor.execute(f"CREATE TEMPORARY TABLE TEST_BANK.{schema}._DRY_RUN_TEST (ID INT)")
                        cursor.execute(f"DROP TABLE TEST_BANK.{schema}._DRY_RUN_TEST")
                        access = "✅ Read + Write"
                    except Exception:
                        access = "✅ Read Only"
                except Exception:
                    access = "❌ No Access"

                print(f"  │ {schema:24s} │ {access:28s} │")

            print("  └──────────────────────────┴──────────────────────────────┘")
            print("\n")

        # ── Summary Matrix ─────────────────────────────────────────────────
        print("=" * 90)
        print("  📊 SUMMARY: SELECT ACCESS MATRIX")
        print("=" * 90)

        # Header
        header = f"  {'ROLE':<28s}"
        for t in TABLES:
            header += f" {t[:5]:>5s}"
        print(header)
        print("  " + "─" * 28 + " " + "─" * (6 * len(TABLES)))

        for role in ROLES:
            try:
                cursor.execute(f"USE ROLE {role}")
                cursor.execute(f"USE DATABASE TEST_BANK")
                cursor.execute(f"USE WAREHOUSE {os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')}")
            except Exception:
                continue

            row = f"  {role:<28s}"
            for table in TABLES:
                allowed, _ = test_select(cursor, table)
                row += f"   {'✅':>3s}" if allowed else f"   {'❌':>3s}"
            print(row)

        print("  " + "─" * 28 + " " + "─" * (6 * len(TABLES)))
        col_legend = f"  {'':28s}"
        for t in TABLES:
            col_legend += f" {t[:5]:>5s}"
        print(col_legend)
        print("=" * 90)

        print("\n🎉 Dry run complete! No data was modified.\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    main()
