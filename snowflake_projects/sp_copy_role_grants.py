"""
Snowflake Native: Copy Role Grants (Stored Procedure)
=======================================================
Runs INSIDE Snowflake as a Python Stored Procedure.
Copies all grants from a source role to a target role.

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
    Runs natively inside Snowflake as a stored procedure.

    Args:
        session:     Snowpark Session (auto-injected by Snowflake)
        source_role: Name of the existing role to copy grants FROM
        target_role: Name of the new/existing role to copy grants TO

    Returns:
        JSON string with full execution report
    """

    report = {
        "source_role": source_role,
        "target_role": target_role,
        "grants_found": 0,
        "successful": 0,
        "skipped": 0,
        "failed": 0,
        "inherited_roles": 0,
        "details": [],
        "errors": [],
        "status": "PENDING"
    }

    try:
        # ── Step 1: Validate source role exists ────────────────────────────
        try:
            session.sql(f"SHOW ROLES LIKE '{source_role}'").collect()
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

        # ── Step 4: Copy each grant ────────────────────────────────────────
        for row in grants_df:
            privilege  = row["privilege"]
            granted_on = row["granted_on"]
            obj_name   = row["name"]
            grant_opt  = row["grant_option"]

            # Skip OWNERSHIP — cannot be transferred via GRANT
            if privilege == "OWNERSHIP":
                report["skipped"] += 1
                report["details"].append(
                    f"SKIP: OWNERSHIP ON {granted_on} {obj_name} (cannot be copied)"
                )
                continue

            # Skip role-to-role grants — handled separately below
            if granted_on == "ROLE":
                report["details"].append(
                    f"SKIP: Role inheritance {obj_name} (handled separately)"
                )
                report["skipped"] += 1
                continue

            # Build GRANT statement
            grant_option_clause = " WITH GRANT OPTION" if grant_opt == "true" else ""
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

        # ── Step 5: Copy role inheritance ──────────────────────────────────
        role_grants = [r for r in grants_df if r["granted_on"] == "ROLE"]
        for rg in role_grants:
            role_name = rg["name"]
            if role_name and role_name != "OWNERSHIP":
                try:
                    inherit_sql = f"GRANT ROLE {role_name} TO ROLE {target_role}"
                    session.sql(inherit_sql).collect()
                    report["inherited_roles"] += 1
                    report["details"].append(f"OK: {inherit_sql}")
                except Exception as e:
                    error_msg = str(e).split('\n')[0][:200]
                    report["errors"].append(
                        f"FAILED: GRANT ROLE {role_name} TO ROLE {target_role} "
                        f"| Error: {error_msg}"
                    )

        # ── Step 6: Grant target role to SYSADMIN ─────────────────────────
        try:
            session.sql(f"GRANT ROLE {target_role} TO ROLE SYSADMIN").collect()
            report["details"].append(
                f"OK: GRANT ROLE {target_role} TO ROLE SYSADMIN"
            )
        except Exception:
            pass  # Non-critical

        # ── Step 7: Verification ──────────────────────────────────────────
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

    # Return concise summary (full details available in report)
    summary_lines = [
        f"{'='*60}",
        f"  COPY ROLE GRANTS — RESULT",
        f"{'='*60}",
        f"  Source:      {report['source_role']}",
        f"  Target:      {report['target_role']}",
        f"  Status:      {report['status']}",
        f"  Grants Found:{report['grants_found']}",
        f"  Successful:  {report['successful']}",
        f"  Skipped:     {report['skipped']}",
        f"  Failed:      {report['failed']}",
        f"  Inherited:   {report['inherited_roles']} role(s)",
    ]

    if "verification" in report:
        v = report["verification"]
        summary_lines.extend([
            f"",
            f"  Verification:",
            f"    Source grants: {v['source_grants']}",
            f"    Target grants: {v['target_grants']}",
            f"    Match: {v['match_percentage']}%",
        ])

    if report["errors"]:
        summary_lines.append(f"\n  Errors ({len(report['errors'])}):")
        for err in report["errors"][:10]:
            summary_lines.append(f"    - {err}")

    summary_lines.append(f"{'='*60}")

    return "\n".join(summary_lines)
'''


# ═══════════════════════════════════════════════════════════════════════════════
#  DEPLOYMENT SCRIPT (runs locally to deploy the stored procedure)
# ═══════════════════════════════════════════════════════════════════════════════

def deploy():
    """Deploy the stored procedure to Snowflake."""
    config = {
        "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
        "user":      os.getenv("SNOWFLAKE_USER"),
        "password":  os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database":  os.getenv("SNOWFLAKE_DATABASE", "TEST_BANK"),
        "role":      "ACCOUNTADMIN",
    }
    config = {k: v for k, v in config.items() if v}

    print("🔗 Connecting to Snowflake...")
    conn = snowflake.connector.connect(**config)
    cursor = conn.cursor()
    print("✅ Connected!\n")

    try:
        # Create the stored procedure
        print("📦 Deploying COPY_ROLE_GRANTS stored procedure...")

        # Ensure we have a schema context
        cursor.execute("USE DATABASE TEST_BANK")
        cursor.execute("USE SCHEMA PUBLIC")

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
COMMENT = 'Copies all grants from source role to target role. Usage: CALL COPY_ROLE_GRANTS(''SOURCE_ROLE'', ''TARGET_ROLE'');'
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
