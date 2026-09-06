"""
Dry Run: Preview COPY_ROLE_GRANTS for ACCOUNTADMIN
====================================================
Connects to Snowflake, fetches all grants for ACCOUNTADMIN,
and shows what would be copied vs ignored — without making changes.
"""

import os
import sys
import snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()


def dry_run():
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
        source_role = "ACCOUNTADMIN"

        print(f"{'='*80}")
        print(f"  DRY RUN — COPY_ROLE_GRANTS for: {source_role}")
        print(f"  (No changes will be made)")
        print(f"{'='*80}\n")

        # Fetch all grants
        cursor.execute(f"SHOW GRANTS TO ROLE {source_role}")
        grants = cursor.fetchall()

        # Get column names from cursor description
        col_names = [desc[0] for desc in cursor.description]
        priv_idx = col_names.index("privilege")
        granted_on_idx = col_names.index("granted_on")
        name_idx = col_names.index("name")
        grant_opt_idx = col_names.index("grant_option")

        print(f"  Total grants found: {len(grants)}\n")

        # Categorize grants
        ownership_grants = []
        object_grants = []
        db_role_grants = []
        account_role_grants = []

        for row in grants:
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
                    "object_type": granted_on,
                    "object_name": obj_name,
                    "action": f"GRANT DATABASE ROLE {obj_name} TO ROLE <TARGET>",
                    "status": "WOULD COPY"
                })
            elif granted_on == "ROLE":
                account_role_grants.append({
                    "privilege": privilege,
                    "object_type": granted_on,
                    "object_name": obj_name,
                    "action": f"GRANT ROLE {obj_name} TO ROLE <TARGET>",
                    "status": "WOULD COPY"
                })
            else:
                grant_opt_str = " WITH GRANT OPTION" if grant_opt == "true" else ""
                if granted_on == "ACCOUNT":
                    action = f"GRANT {privilege} ON ACCOUNT TO ROLE <TARGET>{grant_opt_str}"
                else:
                    action = f"GRANT {privilege} ON {granted_on} {obj_name} TO ROLE <TARGET>{grant_opt_str}"
                object_grants.append({
                    "privilege": privilege,
                    "object_type": granted_on,
                    "object_name": obj_name,
                    "action": action,
                    "status": "WOULD COPY"
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

        # ── Print Object Grants (WOULD COPY) ─────────────────────────────
        print(f"  {'─'*76}")
        print(f"  OBJECT GRANTS — WOULD COPY ({len(object_grants)})")
        print(f"  {'─'*76}")
        print(f"  {'No.':<5} {'Privilege':<20} {'Object Type':<18} {'Object Name':<30} {'Status':<12}")
        print(f"  {'───':<5} {'─────────':<20} {'───────────':<18} {'───────────':<30} {'──────':<12}")
        for idx, g in enumerate(object_grants, 1):
            name_display = g['object_name'][:28] if len(g['object_name']) > 28 else g['object_name']
            print(f"  {idx:<5} {g['privilege']:<20} {g['object_type']:<18} {name_display:<30} {g['status']:<12}")
        print(f"  {'─'*76}\n")

        # ── Print Database Role Grants ────────────────────────────────────
        if db_role_grants:
            print(f"  {'─'*76}")
            print(f"  DATABASE ROLE GRANTS — WOULD COPY ({len(db_role_grants)})")
            print(f"  {'─'*76}")
            print(f"  {'No.':<5} {'Role Name':<40} {'Status':<12}")
            print(f"  {'───':<5} {'─────────':<40} {'──────':<12}")
            for idx, g in enumerate(db_role_grants, 1):
                print(f"  {idx:<5} {g['object_name']:<40} {g['status']:<12}")
            print(f"  {'─'*76}\n")

        # ── Print Account Role Grants ─────────────────────────────────────
        if account_role_grants:
            print(f"  {'─'*76}")
            print(f"  ACCOUNT ROLE INHERITANCE — WOULD COPY ({len(account_role_grants)})")
            print(f"  {'─'*76}")
            print(f"  {'No.':<5} {'Role Name':<40} {'Status':<12}")
            print(f"  {'───':<5} {'─────────':<40} {'──────':<12}")
            for idx, g in enumerate(account_role_grants, 1):
                print(f"  {idx:<5} {g['object_name']:<40} {g['status']:<12}")
            print(f"  {'─'*76}\n")

        # ── Summary ───────────────────────────────────────────────────────
        print(f"  {'='*76}")
        print(f"  DRY RUN SUMMARY")
        print(f"  {'='*76}")
        print(f"  Total Grants:              {len(grants)}")
        print(f"  Ownership (IGNORED):       {len(ownership_grants)}")
        print(f"  Object Grants (WOULD COPY):{len(object_grants)}")
        print(f"  DB Roles (WOULD COPY):     {len(db_role_grants)}")
        print(f"  Acct Roles (WOULD COPY):   {len(account_role_grants)}")
        print(f"  {'='*76}")
        print(f"\n  ⚠️  No changes were made. This was a DRY RUN only.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    dry_run()
