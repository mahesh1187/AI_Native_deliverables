"""
Run COPY_ROLE_GRANTS and generate detailed output report
==========================================================
Calls the stored procedure, then queries both source & target roles
to produce a comprehensive report with ownership ignored list.
"""

import os
import sys
import snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()


def run_and_report():
    source_role = "BANK_DB_ADMIN"
    target_role = "TEST_CLONE_ROLE"

    sf_role = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")

    config = {
        "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
        "user":      os.getenv("SNOWFLAKE_USER"),
        "password":  os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "role":      sf_role,
    }
    config = {k: v for k, v in config.items() if v}

    print("🔗 Connecting to Snowflake...")
    conn = snowflake.connector.connect(**config)
    cursor = conn.cursor()
    print(f"✅ Connected as role: {sf_role}\n")

    try:
        # Use the correct database/schema where the SP is deployed
        cursor.execute("USE DATABASE TEST_BANK")
        cursor.execute("USE SCHEMA ADMIN_TOOLS")

        # ── Step 1: Run the stored procedure ──────────────────────────────
        print(f"{'='*80}")
        print(f"  EXECUTING: CALL COPY_ROLE_GRANTS('{source_role}', '{target_role}')")
        print(f"{'='*80}\n")

        cursor.execute(f"CALL COPY_ROLE_GRANTS('{source_role}', '{target_role}')")
        sp_result = cursor.fetchone()[0]

        print("  📋 Stored Procedure Output:")
        print("  " + "-"*76)
        for line in sp_result.split("\n"):
            print(f"  {line}")
        print("  " + "-"*76)

        # ── Step 2: Fetch source role grants for detailed breakdown ───────
        print(f"\n{'='*80}")
        print(f"  DETAILED GRANT REPORT")
        print(f"{'='*80}\n")

        cursor.execute(f"SHOW GRANTS TO ROLE {source_role}")
        source_grants = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description]
        priv_idx = col_names.index("privilege")
        granted_on_idx = col_names.index("granted_on")
        name_idx = col_names.index("name")
        grant_opt_idx = col_names.index("grant_option")

        # Categorize source grants
        ownership_grants = []
        object_grants = []
        db_role_grants = []
        account_role_grants = []

        for row in source_grants:
            privilege = row[priv_idx]
            granted_on = row[granted_on_idx]
            obj_name = row[name_idx]
            grant_opt = row[grant_opt_idx]

            if privilege == "OWNERSHIP":
                ownership_grants.append({
                    "object_type": granted_on,
                    "object_name": obj_name,
                    "status": "IGNORED"
                })
            elif granted_on == "DATABASE_ROLE":
                db_role_grants.append({
                    "privilege": privilege,
                    "object_name": obj_name,
                    "status": "COPIED"
                })
            elif granted_on == "ROLE":
                account_role_grants.append({
                    "privilege": privilege,
                    "object_name": obj_name,
                    "status": "COPIED"
                })
            else:
                grant_opt_str = " (WITH GRANT OPTION)" if grant_opt == "true" else ""
                object_grants.append({
                    "privilege": privilege,
                    "object_type": granted_on,
                    "object_name": obj_name,
                    "grant_option": grant_opt_str,
                    "status": "COPIED"
                })

        # ── Print Ownership Grants (IGNORED) ──────────────────────────────
        print(f"  {'─'*76}")
        print(f"  OWNERSHIP GRANTS — IGNORED ({len(ownership_grants)})")
        print(f"  {'─'*76}")
        print(f"  {'No.':<5} {'Object Type':<20} {'Object Name':<40} {'Status':<10}")
        print(f"  {'───':<5} {'───────────':<20} {'───────────':<40} {'──────':<10}")
        for idx, own in enumerate(ownership_grants, 1):
            name_display = own['object_name'][:38] if len(own['object_name']) > 38 else own['object_name']
            print(f"  {idx:<5} {own['object_type']:<20} {name_display:<40} {own['status']:<10}")
        print(f"  {'─'*76}\n")

        # ── Print Object Grants (COPIED) ──────────────────────────────────
        print(f"  {'─'*76}")
        print(f"  OBJECT GRANTS — COPIED ({len(object_grants)})")
        print(f"  {'─'*76}")
        print(f"  {'No.':<5} {'Privilege':<22} {'Object Type':<18} {'Object Name':<25} {'Status':<10}")
        print(f"  {'───':<5} {'─────────':<22} {'───────────':<18} {'───────────':<25} {'──────':<10}")
        for idx, g in enumerate(object_grants, 1):
            name_display = g['object_name'][:23] if len(g['object_name']) > 23 else g['object_name']
            priv_display = g['privilege'][:20] if len(g['privilege']) > 20 else g['privilege']
            print(f"  {idx:<5} {priv_display:<22} {g['object_type']:<18} {name_display:<25} {g['status']:<10}")
        print(f"  {'─'*76}\n")

        # ── Print Database Role Grants ────────────────────────────────────
        if db_role_grants:
            print(f"  {'─'*76}")
            print(f"  DATABASE ROLE GRANTS — COPIED ({len(db_role_grants)})")
            print(f"  {'─'*76}")
            print(f"  {'No.':<5} {'Role Name':<40} {'Status':<10}")
            print(f"  {'───':<5} {'─────────':<40} {'──────':<10}")
            for idx, g in enumerate(db_role_grants, 1):
                print(f"  {idx:<5} {g['object_name']:<40} {g['status']:<10}")
            print(f"  {'─'*76}\n")

        # ── Print Account Role Grants ─────────────────────────────────────
        if account_role_grants:
            print(f"  {'─'*76}")
            print(f"  ACCOUNT ROLE INHERITANCE — COPIED ({len(account_role_grants)})")
            print(f"  {'─'*76}")
            print(f"  {'No.':<5} {'Role Name':<40} {'Status':<10}")
            print(f"  {'───':<5} {'─────────':<40} {'──────':<10}")
            for idx, g in enumerate(account_role_grants, 1):
                print(f"  {idx:<5} {g['object_name']:<40} {g['status']:<10}")
            print(f"  {'─'*76}\n")

        # ── Verification: Compare source vs target ────────────────────────
        cursor.execute(f"SHOW GRANTS TO ROLE {target_role}")
        target_grants = cursor.fetchall()

        target_non_ownership = [r for r in target_grants if r[priv_idx] != "OWNERSHIP"]
        source_non_ownership = [r for r in source_grants if r[priv_idx] != "OWNERSHIP"]

        match_pct = round(
            (len(target_non_ownership) / len(source_non_ownership) * 100)
            if source_non_ownership else 100, 1
        )

        print(f"  {'='*76}")
        print(f"  FINAL SUMMARY")
        print(f"  {'='*76}")
        print(f"  Source Role:                {source_role}")
        print(f"  Target Role:               {target_role}")
        print(f"  Total Grants Found:        {len(source_grants)}")
        print(f"  Ownership (IGNORED):       {len(ownership_grants)}")
        print(f"  Object Grants (COPIED):    {len(object_grants)}")
        print(f"  DB Roles (COPIED):         {len(db_role_grants)}")
        print(f"  Acct Roles (COPIED):       {len(account_role_grants)}")
        print(f"  ")
        print(f"  Source grants (non-ownership): {len(source_non_ownership)}")
        print(f"  Target grants (non-ownership): {len(target_non_ownership)}")
        print(f"  Match:                         {match_pct}%")
        print(f"  {'='*76}")

        # ── Cleanup ───────────────────────────────────────────────────────
        print(f"\n  🧹 Cleaning up: DROP ROLE IF EXISTS {target_role}")
        cursor.execute(f"DROP ROLE IF EXISTS {target_role}")
        print(f"  ✅ {target_role} dropped.\n")

        print("  🎉 Done!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        conn.close()
        print("  🔒 Connection closed.")


if __name__ == "__main__":
    run_and_report()
