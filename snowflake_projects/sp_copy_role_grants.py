"""
Snowflake Native: Copy Role Grants (Stored Procedure)
=======================================================
Runs INSIDE Snowflake as a Python Stored Procedure.
Copies all grants from a source role to a target role.
Ownership grants are IGNORED (listed in output with status).

No external dependencies — uses only Snowpark session.

Deployment:
    Run this script from your local machine to deploy the stored procedure.
    Once deployed, call it directly in Snowflake:

        CALL COPY_ROLE_GRANTS('BANK_DB_ADMIN', 'TG_BANK_ADMIN');

Usage from Snowflake Worksheet:
    -- Copy all grants from one role to another
    CALL COPY_ROLE_GRANTS('SOURCE_ROLE', 'TARGET_ROLE');

    -- Example
    CALL COPY_ROLE_GRANTS('BANK_DB_ADMIN', 'NEW_ADMIN_ROLE');
"""

import os
import sys
import snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════════
#  STORED PROCEDURE CODE (runs inside Snowflake)
# ═══════════════════════════════════════════════════════════════════════════════

STORED_PROC_BODY = r'''
import json

def copy_role_grants(session, source_role: str, target_role: str) -> str:
    """
    Copies all grants from source_role to target_role.
    Skips all OWNERSHIP grants (they are listed as IGNORED in the output).
    Runs natively inside Snowflake as a stored procedure.

    Args:
        session:     Snowpark Session (auto-injected by Snowflake)
        source_role: Name of the existing role to copy grants FROM
        target_role: Name of the new/existing role to copy grants TO

    Returns:
        Summary string with full execution report
    """

    report = {
        "source_role": source_role,
        "target_role": target_role,
        "grants_found": 0,
        "successful": 0,
        "skipped": 0,
        "failed": 0,
        "database_roles": 0,
        "inherited_roles": 0,
        "ownership_ignored": [],
        "details": [],
        "errors": [],
        "skipped_details": [],
        "status": "PENDING"
    }

    try:
        # ── Step 1: Validate source role exists ────────────────────────────
        try:
            result = session.sql(f"SHOW ROLES LIKE '{source_role}'").collect()
            if not result:
                report["status"] = "ERROR"
                report["errors"].append(f"Source role '{source_role}' does not exist")
                return json.dumps(report, indent=2)
        except Exception as e:
            report["status"] = "ERROR"
            report["errors"].append(f"Cannot verify source role: {str(e)}")
            return json.dumps(report, indent=2)

        # ── Step 2: Create target role if it doesn't exist ─────────────────
        try:
            session.sql(f"""
                CREATE ROLE IF NOT EXISTS {target_role}
                COMMENT = 'Cloned from {source_role} via COPY_ROLE_GRANTS procedure'
            """).collect()
            report["details"].append(f"Created/verified target role: {target_role}")
        except Exception as e:
            report["status"] = "ERROR"
            report["errors"].append(f"Cannot create target role: {str(e)}")
            return json.dumps(report, indent=2)

        # ── Step 3: Fetch all grants from source role ──────────────────────
        session.sql(f"SHOW GRANTS TO ROLE {source_role}").collect()
        grants_df = session.sql("""
            SELECT "privilege", "granted_on", "name", "grant_option"
            FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
        """).collect()

        report["grants_found"] = len(grants_df)

        # ── Phase 1: Ignore Ownership Grants ──────────────────────────────
        # All OWNERSHIP grants are skipped and collected into a list
        # for reporting purposes only — no transfer is attempted.
        for row in grants_df:
            if row["privilege"] == "OWNERSHIP":
                granted_on = row["granted_on"]
                obj_name   = row["name"]
                report["ownership_ignored"].append({
                    "object_type": granted_on,
                    "object_name": obj_name,
                    "status": "IGNORED"
                })

        # ── Phase 2: Copy Object Grants ───────────────────────────────────
        for row in grants_df:
            privilege  = row["privilege"]
            granted_on = row["granted_on"]
            obj_name   = row["name"]
            grant_opt  = row["grant_option"]

            # Skip OWNERSHIP — ignored entirely
            if privilege == "OWNERSHIP":
                continue

            # Skip role grants — handled in Phase 3 and Phase 4
            if granted_on in ("ROLE", "DATABASE_ROLE"):
                report["skipped"] += 1
                phase = "Phase 3 (Database Roles)" if granted_on == "DATABASE_ROLE" else "Phase 4 (Account Roles)"
                report["skipped_details"].append(
                    f"{privilege} ON {granted_on} {obj_name} "
                    f"| Reason: Handled in {phase}"
                )
                continue

            # Build GRANT statement
            grant_option_clause = " WITH GRANT OPTION" if grant_opt == "true" else ""

            # ACCOUNT-level grants: syntax is "GRANT ... ON ACCOUNT"
            if granted_on == "ACCOUNT":
                grant_sql = (
                    f"GRANT {privilege} ON ACCOUNT "
                    f"TO ROLE {target_role}{grant_option_clause}"
                )
            else:
                grant_sql = (
                    f"GRANT {privilege} ON {granted_on} {obj_name} "
                    f"TO ROLE {target_role}{grant_option_clause}"
                )

            try:
                session.sql(grant_sql).collect()
                report["successful"] += 1
                report["details"].append(f"OK: {grant_sql}")
            except Exception as e:
                error_msg = str(e).split('\n')[0][:200]
                report["failed"] += 1
                report["errors"].append(f"FAILED: {grant_sql} | Error: {error_msg}")

        # ── Phase 3: Copy Database Role Grants ────────────────────────────
        db_role_grants = [r for r in grants_df if r["granted_on"] == "DATABASE_ROLE"]
        for rg in db_role_grants:
            role_name = rg["name"]
            if role_name:
                try:
                    db_role_sql = f"GRANT DATABASE ROLE {role_name} TO ROLE {target_role}"
                    session.sql(db_role_sql).collect()
                    report["database_roles"] += 1
                    report["details"].append(f"OK: {db_role_sql}")
                except Exception as e:
                    error_msg = str(e).split('\n')[0][:200]
                    report["failed"] += 1
                    report["errors"].append(
                        f"FAILED: GRANT DATABASE ROLE {role_name} TO ROLE {target_role} "
                        f"| Error: {error_msg}"
                    )

        # ── Phase 4: Copy Account Role Inheritance ────────────────────────
        account_role_grants = [r for r in grants_df if r["granted_on"] == "ROLE"]
        for rg in account_role_grants:
            role_name = rg["name"]
            if role_name:
                try:
                    inherit_sql = f"GRANT ROLE {role_name} TO ROLE {target_role}"
                    session.sql(inherit_sql).collect()
                    report["inherited_roles"] += 1
                    report["details"].append(f"OK: {inherit_sql}")
                except Exception as e:
                    error_msg = str(e).split('\n')[0][:200]
                    report["failed"] += 1
                    report["errors"].append(
                        f"FAILED: GRANT ROLE {role_name} TO ROLE {target_role} "
                        f"| Error: {error_msg}"
                    )

        # ── Phase 5: Grant target role to SYSADMIN ────────────────────────
        try:
            session.sql(f"GRANT ROLE {target_role} TO ROLE SYSADMIN").collect()
            report["details"].append(
                f"OK: GRANT ROLE {target_role} TO ROLE SYSADMIN"
            )
        except Exception:
            pass  # Non-critical

        # ── Phase 6: Verification ─────────────────────────────────────────
        session.sql(f"SHOW GRANTS TO ROLE {source_role}").collect()
        source_count_df = session.sql("""
            SELECT COUNT(*) AS CNT
            FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
            WHERE "privilege" != 'OWNERSHIP'
        """).collect()

        session.sql(f"SHOW GRANTS TO ROLE {target_role}").collect()
        target_count_df = session.sql("""
            SELECT COUNT(*) AS CNT
            FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
            WHERE "privilege" != 'OWNERSHIP'
        """).collect()

        source_count = source_count_df[0]["CNT"] if source_count_df else 0
        target_count = target_count_df[0]["CNT"] if target_count_df else 0

        report["verification"] = {
            "source_grants": source_count,
            "target_grants": target_count,
            "match_percentage": round(
                (target_count / source_count * 100) if source_count > 0 else 100, 1
            )
        }

        # ── Final status ──────────────────────────────────────────────────
        if report["failed"] == 0:
            report["status"] = "SUCCESS"
        else:
            report["status"] = "PARTIAL"

    except Exception as e:
        report["status"] = "ERROR"
        report["errors"].append(f"Unexpected error: {str(e)}")

    # ── Build output summary ──────────────────────────────────────────────
    summary_lines = [
        f"{'='*65}",
        f"  COPY ROLE GRANTS — RESULT",
        f"{'='*65}",
        f"  Source:      {report['source_role']}",
        f"  Target:      {report['target_role']}",
        f"  Status:      {report['status']}",
        f"  Grants Found:{report['grants_found']}",
        f"",
        f"  Phase 2 — Object Grants: {report['successful']} granted",
        f"  Phase 3 — DB Roles:      {report['database_roles']} granted",
        f"  Phase 4 — Acct Roles:    {report['inherited_roles']} inherited",
        f"",
        f"  Failed:      {report['failed']}",
        f"  Skipped:     {report['skipped']}",
    ]

    # ── Ownership Ignored List ────────────────────────────────────────────
    if report["ownership_ignored"]:
        summary_lines.extend([
            f"",
            f"  {'─'*61}",
            f"  OWNERSHIP GRANTS — IGNORED ({len(report['ownership_ignored'])})",
            f"  {'─'*61}",
            f"  {'No.':<5} {'Object Type':<20} {'Object Name':<30} {'Status':<10}",
            f"  {'───':<5} {'───────────':<20} {'───────────':<30} {'──────':<10}",
        ])
        for idx, own in enumerate(report["ownership_ignored"], 1):
            summary_lines.append(
                f"  {idx:<5} {own['object_type']:<20} {own['object_name']:<30} {own['status']:<10}"
            )
        summary_lines.append(f"  {'─'*61}")

    # ── Verification ──────────────────────────────────────────────────────
    if "verification" in report:
        v = report["verification"]
        summary_lines.extend([
            f"",
            f"  Verification:",
            f"    Source grants (non-ownership): {v['source_grants']}",
            f"    Target grants (non-ownership): {v['target_grants']}",
            f"    Match: {v['match_percentage']}%",
        ])

    if report["skipped_details"]:
        summary_lines.append(f"\n  Skipped ({len(report['skipped_details'])}):")
        for skip in report["skipped_details"]:
            summary_lines.append(f"    - {skip}")

    if report["errors"]:
        summary_lines.append(f"\n  Errors ({len(report['errors'])}):")
        for err in report["errors"][:10]:
            summary_lines.append(f"    - {err}")

    summary_lines.append(f"{'='*65}")

    return "\n".join(summary_lines)
'''


# ═══════════════════════════════════════════════════════════════════════════════
#  DEPLOYMENT SCRIPT (runs locally to deploy the stored procedure)
# ═══════════════════════════════════════════════════════════════════════════════

def deploy():
    """Deploy the stored procedure to Snowflake."""
    sf_database = os.getenv("SNOWFLAKE_DATABASE", "TEST_BANK")
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
        # Verify role and database access
        sf_schema = "ADMIN_TOOLS"
        print(f"📋 Setting up: {sf_database}.{sf_schema}...")
        try:
            cursor.execute(f"USE ROLE {sf_role}")
            cursor.execute(f"USE DATABASE {sf_database}")
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {sf_schema} COMMENT = 'Admin stored procedures and utilities'")
            cursor.execute(f"USE SCHEMA {sf_schema}")
            print(f"✅ Access verified: {sf_role} → {sf_database}.{sf_schema}\n")
        except Exception as e:
            print(f"\n❌ Access error: {e}")
            print(f"\n💡 Troubleshooting:")
            print(f"   1. Verify role:  SHOW GRANTS TO USER {os.getenv('SNOWFLAKE_USER')};")
            print(f"   2. Verify DB:    SHOW DATABASES LIKE '{sf_database}';")
            print(f"   3. Grant access: GRANT USAGE ON DATABASE {sf_database} TO ROLE {sf_role};")
            raise

        # Create the stored procedure
        print("📦 Deploying COPY_ROLE_GRANTS stored procedure...")

        deploy_sql = f"""
CREATE OR REPLACE PROCEDURE COPY_ROLE_GRANTS(
    SOURCE_ROLE VARCHAR,
    TARGET_ROLE VARCHAR
)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'copy_role_grants'
COMMENT = 'Copies all grants from source role to target role (ownership ignored). Usage: CALL COPY_ROLE_GRANTS(''SOURCE_ROLE'', ''TARGET_ROLE'');'
EXECUTE AS CALLER
AS
$${STORED_PROC_BODY}$$;
"""
        cursor.execute(deploy_sql)
        print("✅ Stored procedure COPY_ROLE_GRANTS deployed successfully!\n")

        # Grant execute to SYSADMIN and ACCOUNTADMIN
        cursor.execute("GRANT USAGE ON PROCEDURE COPY_ROLE_GRANTS(VARCHAR, VARCHAR) TO ROLE SYSADMIN")
        print("✅ Granted USAGE to SYSADMIN\n")

        # Show usage instructions
        print("=" * 65)
        print("  📋 USAGE INSTRUCTIONS")
        print("=" * 65)
        print()
        print("  Run these commands in any Snowflake Worksheet or SnowSQL:")
        print()
        print("  -- Copy all grants from BANK_DB_ADMIN to a new role")
        print("  CALL COPY_ROLE_GRANTS('BANK_DB_ADMIN', 'MY_NEW_ADMIN');")
        print()
        print("  -- Clone any role to another")
        print("  CALL COPY_ROLE_GRANTS('SOURCE_ROLE', 'TARGET_ROLE');")
        print()
        print("  -- The procedure returns a detailed report with:")
        print("  --   • Grant counts (found, copied, skipped, failed)")
        print("  --   • Role inheritance details")
        print("  --   • Ownership grants listed as IGNORED with status")
        print("  --   • Verification (source vs target match %)")
        print("  --   • Error details if any grants failed")
        print()
        print("=" * 65)

        # ── Quick test ─────────────────────────────────────────────────────
        print("\n🧪 Running quick test: COPY_ROLE_GRANTS('BANK_DB_ADMIN', 'TEST_CLONE_ROLE')...\n")

        cursor.execute("CALL COPY_ROLE_GRANTS('BANK_DB_ADMIN', 'TEST_CLONE_ROLE')")
        result = cursor.fetchone()[0]
        print(result)

        # Cleanup test role
        print("\n🧹 Cleaning up test role...")
        cursor.execute("DROP ROLE IF EXISTS TEST_CLONE_ROLE")
        print("✅ TEST_CLONE_ROLE dropped.\n")

        print("🎉 Deployment complete! The procedure is ready to use in Snowflake.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    deploy()
