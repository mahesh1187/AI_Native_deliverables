"""
Snowflake SCIM Integration — Azure AD (Microsoft Entra ID)
============================================================
Creates a SCIM security integration and generates an access token
so that Azure AD can provision users and groups into Snowflake.

Prerequisites:
    • ACCOUNTADMIN role (or a role with CREATE INTEGRATION privilege)
    • The SNOWFLAKE_ACCOUNT value in .env must be the full account URL
      (e.g. xy12345.us-east-1)

What this script does:
    1. Creates (or replaces) a security integration of type SCIM
    2. Creates a dedicated SCIM token for the integration
    3. Prints the token and the SCIM endpoint URL you'll paste into
       Azure AD → Enterprise App → Provisioning settings

Usage:
    python create_scim_integration.py
    python create_scim_integration.py --dry-run
"""

import os
import sys
import argparse
import snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()


# ─── Configuration ─────────────────────────────────────────────────────────────

# Integration name — change if you need multiple SCIM integrations
SCIM_INTEGRATION_NAME = "AAD_SCIM_INTEGRATION"

# Network policy to attach (optional — leave empty to skip)
SCIM_NETWORK_POLICY = os.getenv("SCIM_NETWORK_POLICY", "")

SNOWFLAKE_CONFIG = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
    "user":      os.getenv("SNOWFLAKE_USER"),
    "password":  os.getenv("SNOWFLAKE_PASSWORD"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database":  os.getenv("SNOWFLAKE_DATABASE"),
    "schema":    os.getenv("SNOWFLAKE_SCHEMA"),
    "role":      os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def get_connection():
    """Create and return a Snowflake connection using .env credentials."""
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


def run_query(conn, query, suppress_output=False):
    """Execute a query and return the results as a list of dicts."""
    cursor = conn.cursor(snowflake.connector.DictCursor)
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except snowflake.connector.errors.ProgrammingError as e:
        if not suppress_output:
            print(f"   ⚠️  Query error: {e}")
        return []
    finally:
        cursor.close()


def execute_sql(conn, sql, description, dry_run=False):
    """Execute a SQL statement with logging."""
    print(f"\n{'🔍' if dry_run else '▶️ '} {description}")
    if dry_run:
        print(f"   [DRY RUN] SQL:\n   {sql.strip()}")
        return []
    else:
        print(f"   SQL: {sql.strip()[:120]}{'...' if len(sql.strip()) > 120 else ''}")
        result = run_query(conn, sql)
        print(f"   ✅ Done")
        return result


# ─── SCIM Integration Steps ───────────────────────────────────────────────────

def verify_role(conn, dry_run=False):
    """Verify the current role has privileges to create integrations."""
    print("\n" + "=" * 65)
    print("  STEP 0 — VERIFY ROLE & PRIVILEGES")
    print("=" * 65)

    if dry_run:
        print("   [DRY RUN] Would check current role")
        return True

    result = run_query(conn, "SELECT CURRENT_ROLE() AS role")
    role = result[0]["ROLE"] if result else "UNKNOWN"
    print(f"   🎭 Current role: {role}")

    if role != "ACCOUNTADMIN":
        print("   ⚠️  WARNING: You are not using ACCOUNTADMIN.")
        print("   SCIM integration creation typically requires ACCOUNTADMIN.")
        print("   Proceeding anyway — the command will fail if privileges are insufficient.")

    return True


def create_scim_integration(conn, dry_run=False):
    """Create (or replace) the Azure AD SCIM security integration."""
    print("\n" + "=" * 65)
    print("  STEP 1 — CREATE SCIM SECURITY INTEGRATION")
    print("=" * 65)

    sql = f"""
CREATE OR REPLACE SECURITY INTEGRATION {SCIM_INTEGRATION_NAME}
    TYPE = SCIM
    SCIM_CLIENT = 'AZURE'
    RUN_AS_ROLE = 'AAD_PROVISIONER'
    ENABLED = TRUE
    COMMENT = 'Azure AD SCIM integration for automated user/group provisioning'
""".strip()

    # First ensure the AAD_PROVISIONER role exists
    execute_sql(
        conn,
        "CREATE ROLE IF NOT EXISTS AAD_PROVISIONER COMMENT = 'Role used by Azure AD SCIM provisioning'",
        "Creating AAD_PROVISIONER role (if not exists)",
        dry_run=dry_run,
    )

    # Grant ACCOUNTADMIN's CREATE USER and CREATE ROLE to AAD_PROVISIONER
    execute_sql(
        conn,
        "GRANT CREATE USER ON ACCOUNT TO ROLE AAD_PROVISIONER",
        "Granting CREATE USER on account to AAD_PROVISIONER",
        dry_run=dry_run,
    )
    execute_sql(
        conn,
        "GRANT CREATE ROLE ON ACCOUNT TO ROLE AAD_PROVISIONER",
        "Granting CREATE ROLE on account to AAD_PROVISIONER",
        dry_run=dry_run,
    )

    # Grant AAD_PROVISIONER to ACCOUNTADMIN so the integration can use it
    execute_sql(
        conn,
        "GRANT ROLE AAD_PROVISIONER TO ROLE ACCOUNTADMIN",
        "Granting AAD_PROVISIONER role to ACCOUNTADMIN",
        dry_run=dry_run,
    )

    # Create the integration
    execute_sql(conn, sql, "Creating SCIM security integration", dry_run=dry_run)

    # Optionally attach a network policy
    if SCIM_NETWORK_POLICY:
        execute_sql(
            conn,
            f"ALTER SECURITY INTEGRATION {SCIM_INTEGRATION_NAME} SET NETWORK_POLICY = {SCIM_NETWORK_POLICY}",
            f"Attaching network policy '{SCIM_NETWORK_POLICY}'",
            dry_run=dry_run,
        )


def generate_scim_token(conn, dry_run=False):
    """Generate an OAuth access token for the SCIM integration."""
    print("\n" + "=" * 65)
    print("  STEP 2 — GENERATE SCIM ACCESS TOKEN")
    print("=" * 65)

    if dry_run:
        print("   [DRY RUN] Would execute:")
        print(f"   SELECT SYSTEM$GENERATE_SCIM_ACCESS_TOKEN('{SCIM_INTEGRATION_NAME}')")
        return None

    result = run_query(
        conn,
        f"SELECT SYSTEM$GENERATE_SCIM_ACCESS_TOKEN('{SCIM_INTEGRATION_NAME}') AS TOKEN"
    )

    if result and "TOKEN" in result[0]:
        token = result[0]["TOKEN"]
        print("   ✅ Token generated successfully")
        return token
    else:
        print("   ❌ Failed to generate token. Check that the integration exists and you have ACCOUNTADMIN.")
        return None


def describe_integration(conn, dry_run=False):
    """Show details of the created integration."""
    print("\n" + "=" * 65)
    print("  STEP 3 — DESCRIBE INTEGRATION")
    print("=" * 65)

    if dry_run:
        print(f"   [DRY RUN] Would run: DESCRIBE SECURITY INTEGRATION {SCIM_INTEGRATION_NAME}")
        return

    results = run_query(conn, f"DESCRIBE SECURITY INTEGRATION {SCIM_INTEGRATION_NAME}")
    if results:
        print(f"\n   📋 Integration details for '{SCIM_INTEGRATION_NAME}':")
        print("   " + "-" * 55)
        for row in results:
            prop = row.get("property", row.get("PROPERTY", ""))
            val = row.get("property_value", row.get("PROPERTY_VALUE", ""))
            print(f"   {prop:<35} {val}")
        print("   " + "-" * 55)


def print_azure_setup_instructions(token, account):
    """Print the values to paste into Azure AD provisioning settings."""
    print("\n" + "=" * 65)
    print("  🔧 AZURE AD PROVISIONING SETUP")
    print("=" * 65)

    scim_endpoint = f"https://{account}.snowflakecomputing.com/scim/v2"

    print(f"""
   Copy these values into Azure AD → Enterprise App → Provisioning:

   ┌─────────────────────────────────────────────────────────────┐
   │  Tenant URL:                                               │
   │  {scim_endpoint:<57} │
   │                                                             │
   │  Secret Token:                                              │
   │  {token[:50] + '...' if token and len(token) > 50 else (token or 'N/A'):<57} │
   └─────────────────────────────────────────────────────────────┘

   ⚠️  IMPORTANT NOTES:
   • The token expires after 6 months. Set a calendar reminder to
     regenerate it before expiry by re-running this script.
   • Store the token securely — treat it like a password.
   • In Azure AD, set the provisioning mode to "Automatic".
   • Map Azure AD attributes to Snowflake SCIM attributes as needed.
""")


def show_summary(dry_run=False):
    """Print a summary of what was created."""
    print("\n" + "=" * 65)
    if dry_run:
        print("  📝 DRY RUN COMPLETE — No changes were made")
    else:
        print("  ✅ SCIM INTEGRATION SETUP COMPLETE")
    print("=" * 65)

    if not dry_run:
        print("""
   What was created:
   ─────────────────
   1. Role:         AAD_PROVISIONER
   2. Grants:       CREATE USER, CREATE ROLE on ACCOUNT → AAD_PROVISIONER
   3. Integration:  {name} (type=SCIM, client=AZURE)
   4. Token:        OAuth access token for SCIM provisioning

   Next steps:
   ───────────
   • Paste the Tenant URL and Secret Token into Azure AD
   • Configure attribute mappings in Azure AD
   • Test provisioning with a single user first
   • Enable automatic provisioning once validated
""".format(name=SCIM_INTEGRATION_NAME))


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    global SCIM_INTEGRATION_NAME

    parser = argparse.ArgumentParser(
        description="Create Snowflake SCIM integration for Azure AD"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview SQL statements without executing them",
    )
    parser.add_argument(
        "--integration-name",
        type=str,
        default=None,
        help=f"Custom integration name (default: {SCIM_INTEGRATION_NAME})",
    )
    args = parser.parse_args()

    if args.integration_name:
        SCIM_INTEGRATION_NAME = args.integration_name

    print("\n" + "🔷" * 30)
    print("  SNOWFLAKE SCIM INTEGRATION — AZURE AD SETUP")
    print("🔷" * 30)

    if args.dry_run:
        print("\n   ⚡ DRY RUN MODE — no changes will be made\n")

    conn = get_connection()

    try:
        # Step 0: Verify role
        verify_role(conn, dry_run=args.dry_run)

        # Step 1: Create integration
        create_scim_integration(conn, dry_run=args.dry_run)

        # Step 2: Generate token
        token = generate_scim_token(conn, dry_run=args.dry_run)

        # Step 3: Describe the integration
        describe_integration(conn, dry_run=args.dry_run)

        # Print Azure AD setup instructions
        if token:
            account = os.getenv("SNOWFLAKE_ACCOUNT", "your_account")
            print_azure_setup_instructions(token, account)

        # Summary
        show_summary(dry_run=args.dry_run)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

    finally:
        conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    main()
