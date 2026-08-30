"""
Snowflake Role Hierarchy — Production-Grade Setup
====================================================
Creates a realistic, production-like role hierarchy for the
TEST_BANK database with least-privilege access controls.

Role Hierarchy:
    ACCOUNTADMIN
    ├── SYSADMIN
    │   ├── BANK_DB_ADMIN          — Full control over TEST_BANK database
    │   ├── BANK_DATA_ENGINEER     — ETL & pipeline operations
    │   ├── BANK_DATA_ANALYST      — Read + reporting access
    │   ├── BANK_DATA_SCIENTIST    — Read + sandbox/experimentation
    │   └── BANK_APP_SERVICE       — Application service account (limited)
    ├── SECURITYADMIN
    │   └── BANK_ROLE_ADMIN        — Manages bank-specific roles
    └── USERADMIN
    
    Additional functional roles (granted to SYSADMIN):
    ├── BANK_COMPLIANCE_OFFICER    — Audit & compliance (read-all)
    ├── BANK_BRANCH_MANAGER        — Branch-level operations
    ├── BANK_TELLER                — Teller counter operations
    ├── BANK_LOAN_OFFICER          — Loan processing
    └── BANK_CUSTOMER_SERVICE      — Customer support (read-only sensitive)

Usage:
    python create_role_hierarchy.py
"""

import os
import sys
import snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()


# ─── Role Definitions ─────────────────────────────────────────────────────────

ROLES = {
    # ── Administrative Roles ───────────────────────────────────────────────
    "BANK_DB_ADMIN": {
        "comment": "Full administrative control over TEST_BANK database — DDL, DML, and grant privileges",
        "parent": "SYSADMIN"
    },
    "BANK_ROLE_ADMIN": {
        "comment": "Manages bank-specific custom roles and user-role assignments",
        "parent": "SECURITYADMIN"
    },

    # ── Data Team Roles ────────────────────────────────────────────────────
    "BANK_DATA_ENGINEER": {
        "comment": "ETL pipelines, data ingestion, schema modifications in staging areas",
        "parent": "SYSADMIN"
    },
    "BANK_DATA_ANALYST": {
        "comment": "Read-only access to production data, write access to analytics schema",
        "parent": "SYSADMIN"
    },
    "BANK_DATA_SCIENTIST": {
        "comment": "Read access to production data, full access to sandbox schema for experimentation",
        "parent": "SYSADMIN"
    },

    # ── Application Roles ─────────────────────────────────────────────────
    "BANK_APP_SERVICE": {
        "comment": "Application service account — restricted read/write on operational tables only",
        "parent": "SYSADMIN"
    },

    # ── Functional / Business Roles ────────────────────────────────────────
    "BANK_COMPLIANCE_OFFICER": {
        "comment": "Audit & regulatory compliance — read-all access including sensitive data",
        "parent": "SYSADMIN"
    },
    "BANK_BRANCH_MANAGER": {
        "comment": "Branch-level operational access — customers, accounts, loans",
        "parent": "SYSADMIN"
    },
    "BANK_LOAN_OFFICER": {
        "comment": "Loan processing and management — loans, payments, customer info",
        "parent": "SYSADMIN"
    },
    "BANK_TELLER": {
        "comment": "Counter operations — transactions, basic account lookups",
        "parent": "SYSADMIN"
    },
    "BANK_CUSTOMER_SERVICE": {
        "comment": "Customer support — read-only access to customer and account info (masked sensitive data)",
        "parent": "SYSADMIN"
    },
    "BANK_READ_ONLY": {
        "comment": "Baseline read-only access to non-sensitive BANK schema tables",
        "parent": "SYSADMIN"
    },
}


# ─── Grant Definitions ────────────────────────────────────────────────────────

# Database & schema level grants
DB_GRANTS = {
    "BANK_DB_ADMIN": [
        "GRANT ALL PRIVILEGES ON DATABASE TEST_BANK TO ROLE BANK_DB_ADMIN",
        "GRANT ALL PRIVILEGES ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DB_ADMIN",
        "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_DB_ADMIN",
        "GRANT ALL PRIVILEGES ON FUTURE TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_DB_ADMIN",
        "GRANT CREATE SCHEMA ON DATABASE TEST_BANK TO ROLE BANK_DB_ADMIN",
    ],

    "BANK_DATA_ENGINEER": [
        "GRANT USAGE ON DATABASE TEST_BANK TO ROLE BANK_DATA_ENGINEER",
        "GRANT USAGE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ENGINEER",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ENGINEER",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON FUTURE TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ENGINEER",
        "GRANT CREATE TABLE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ENGINEER",
        "GRANT CREATE VIEW ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ENGINEER",
        "GRANT CREATE STAGE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ENGINEER",
        "GRANT CREATE FILE FORMAT ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ENGINEER",
        "GRANT CREATE PIPE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ENGINEER",
        "GRANT CREATE STREAM ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ENGINEER",
        "GRANT CREATE TASK ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ENGINEER",
    ],

    "BANK_DATA_ANALYST": [
        "GRANT USAGE ON DATABASE TEST_BANK TO ROLE BANK_DATA_ANALYST",
        "GRANT USAGE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ANALYST",
        "GRANT SELECT ON ALL TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ANALYST",
        "GRANT SELECT ON FUTURE TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ANALYST",
        "GRANT CREATE VIEW ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_ANALYST",
    ],

    "BANK_DATA_SCIENTIST": [
        "GRANT USAGE ON DATABASE TEST_BANK TO ROLE BANK_DATA_SCIENTIST",
        "GRANT USAGE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_SCIENTIST",
        "GRANT SELECT ON ALL TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_SCIENTIST",
        "GRANT SELECT ON FUTURE TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_DATA_SCIENTIST",
    ],

    "BANK_APP_SERVICE": [
        "GRANT USAGE ON DATABASE TEST_BANK TO ROLE BANK_APP_SERVICE",
        "GRANT USAGE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_APP_SERVICE",
        # App can read customers, accounts; insert/update transactions
        "GRANT SELECT ON TABLE TEST_BANK.BANK.CUSTOMERS TO ROLE BANK_APP_SERVICE",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.ACCOUNTS TO ROLE BANK_APP_SERVICE",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.BRANCHES TO ROLE BANK_APP_SERVICE",
        "GRANT SELECT, INSERT ON TABLE TEST_BANK.BANK.TRANSACTIONS TO ROLE BANK_APP_SERVICE",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.CARDS TO ROLE BANK_APP_SERVICE",
    ],

    "BANK_COMPLIANCE_OFFICER": [
        "GRANT USAGE ON DATABASE TEST_BANK TO ROLE BANK_COMPLIANCE_OFFICER",
        "GRANT USAGE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_COMPLIANCE_OFFICER",
        "GRANT SELECT ON ALL TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_COMPLIANCE_OFFICER",
        "GRANT SELECT ON FUTURE TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_COMPLIANCE_OFFICER",
    ],

    "BANK_BRANCH_MANAGER": [
        "GRANT USAGE ON DATABASE TEST_BANK TO ROLE BANK_BRANCH_MANAGER",
        "GRANT USAGE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_BRANCH_MANAGER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.BRANCHES TO ROLE BANK_BRANCH_MANAGER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.CUSTOMERS TO ROLE BANK_BRANCH_MANAGER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.ACCOUNTS TO ROLE BANK_BRANCH_MANAGER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.TRANSACTIONS TO ROLE BANK_BRANCH_MANAGER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.EMPLOYEES TO ROLE BANK_BRANCH_MANAGER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.LOANS TO ROLE BANK_BRANCH_MANAGER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.LOAN_PAYMENTS TO ROLE BANK_BRANCH_MANAGER",
    ],

    "BANK_LOAN_OFFICER": [
        "GRANT USAGE ON DATABASE TEST_BANK TO ROLE BANK_LOAN_OFFICER",
        "GRANT USAGE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_LOAN_OFFICER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.CUSTOMERS TO ROLE BANK_LOAN_OFFICER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.ACCOUNTS TO ROLE BANK_LOAN_OFFICER",
        "GRANT SELECT, INSERT, UPDATE ON TABLE TEST_BANK.BANK.LOANS TO ROLE BANK_LOAN_OFFICER",
        "GRANT SELECT, INSERT ON TABLE TEST_BANK.BANK.LOAN_PAYMENTS TO ROLE BANK_LOAN_OFFICER",
    ],

    "BANK_TELLER": [
        "GRANT USAGE ON DATABASE TEST_BANK TO ROLE BANK_TELLER",
        "GRANT USAGE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_TELLER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.CUSTOMERS TO ROLE BANK_TELLER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.ACCOUNTS TO ROLE BANK_TELLER",
        "GRANT SELECT, INSERT ON TABLE TEST_BANK.BANK.TRANSACTIONS TO ROLE BANK_TELLER",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.BRANCHES TO ROLE BANK_TELLER",
    ],

    "BANK_CUSTOMER_SERVICE": [
        "GRANT USAGE ON DATABASE TEST_BANK TO ROLE BANK_CUSTOMER_SERVICE",
        "GRANT USAGE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_CUSTOMER_SERVICE",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.CUSTOMERS TO ROLE BANK_CUSTOMER_SERVICE",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.ACCOUNTS TO ROLE BANK_CUSTOMER_SERVICE",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.CARDS TO ROLE BANK_CUSTOMER_SERVICE",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.BRANCHES TO ROLE BANK_CUSTOMER_SERVICE",
        "GRANT SELECT ON TABLE TEST_BANK.BANK.TRANSACTIONS TO ROLE BANK_CUSTOMER_SERVICE",
    ],

    "BANK_READ_ONLY": [
        "GRANT USAGE ON DATABASE TEST_BANK TO ROLE BANK_READ_ONLY",
        "GRANT USAGE ON SCHEMA TEST_BANK.BANK TO ROLE BANK_READ_ONLY",
        "GRANT SELECT ON ALL TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_READ_ONLY",
        "GRANT SELECT ON FUTURE TABLES IN SCHEMA TEST_BANK.BANK TO ROLE BANK_READ_ONLY",
    ],
}

# Warehouse grants — different sizes for different roles
WAREHOUSE_GRANTS = {
    "BANK_DB_ADMIN":            "ALL PRIVILEGES",
    "BANK_DATA_ENGINEER":       "USAGE, OPERATE, MONITOR",
    "BANK_DATA_ANALYST":        "USAGE",
    "BANK_DATA_SCIENTIST":      "USAGE",
    "BANK_APP_SERVICE":         "USAGE",
    "BANK_COMPLIANCE_OFFICER":  "USAGE",
    "BANK_BRANCH_MANAGER":      "USAGE",
    "BANK_LOAN_OFFICER":        "USAGE",
    "BANK_TELLER":              "USAGE",
    "BANK_CUSTOMER_SERVICE":    "USAGE",
    "BANK_READ_ONLY":           "USAGE",
}

# Role inheritance: functional roles inherit from base roles
ROLE_INHERITANCE = [
    # Branch manager inherits read-only as a baseline
    ("BANK_READ_ONLY", "BANK_BRANCH_MANAGER"),
    # Analyst inherits read-only
    ("BANK_READ_ONLY", "BANK_DATA_ANALYST"),
    # Data scientist inherits analyst
    ("BANK_DATA_ANALYST", "BANK_DATA_SCIENTIST"),
    # Data engineer inherits analyst
    ("BANK_DATA_ANALYST", "BANK_DATA_ENGINEER"),
    # DB admin inherits data engineer
    ("BANK_DATA_ENGINEER", "BANK_DB_ADMIN"),
]

# Additional schemas for analyst/scientist sandboxes
ADDITIONAL_SCHEMAS = [
    {
        "name": "ANALYTICS",
        "comment": "Reporting and analytics workspace for data analysts",
        "grants": {
            "BANK_DATA_ANALYST": "ALL PRIVILEGES",
            "BANK_DATA_SCIENTIST": "USAGE, CREATE VIEW",
            "BANK_DB_ADMIN": "ALL PRIVILEGES",
        }
    },
    {
        "name": "SANDBOX",
        "comment": "Experimentation workspace for data scientists",
        "grants": {
            "BANK_DATA_SCIENTIST": "ALL PRIVILEGES",
            "BANK_DB_ADMIN": "ALL PRIVILEGES",
        }
    },
    {
        "name": "STAGING",
        "comment": "Data ingestion staging area for ETL pipelines",
        "grants": {
            "BANK_DATA_ENGINEER": "ALL PRIVILEGES",
            "BANK_DB_ADMIN": "ALL PRIVILEGES",
        }
    },
]

# Masking policies for sensitive data
MASKING_POLICIES = [
    # PAN number masking — only compliance and admin see full value
    {
        "name": "BANK.MASK_PAN",
        "signature": "(val STRING)",
        "returns": "STRING",
        "body": """
            CASE
                WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'BANK_DB_ADMIN', 'BANK_COMPLIANCE_OFFICER')
                    THEN val
                WHEN CURRENT_ROLE() IN ('BANK_BRANCH_MANAGER', 'BANK_LOAN_OFFICER')
                    THEN CONCAT('XXXXX', RIGHT(val, 4))
                ELSE '**MASKED**'
            END
        """,
        "apply_to": ("BANK.CUSTOMERS", "PAN_NUMBER")
    },
    # Aadhar masking
    {
        "name": "BANK.MASK_AADHAR",
        "signature": "(val STRING)",
        "returns": "STRING",
        "body": """
            CASE
                WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'BANK_DB_ADMIN', 'BANK_COMPLIANCE_OFFICER')
                    THEN val
                WHEN CURRENT_ROLE() IN ('BANK_BRANCH_MANAGER', 'BANK_LOAN_OFFICER')
                    THEN CONCAT('XXXXXXXX', RIGHT(val, 4))
                ELSE '**MASKED**'
            END
        """,
        "apply_to": ("BANK.CUSTOMERS", "AADHAR_NUMBER")
    },
    # Email masking
    {
        "name": "BANK.MASK_EMAIL",
        "signature": "(val STRING)",
        "returns": "STRING",
        "body": """
            CASE
                WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'BANK_DB_ADMIN', 'BANK_COMPLIANCE_OFFICER',
                                        'BANK_BRANCH_MANAGER', 'BANK_DATA_ANALYST')
                    THEN val
                ELSE CONCAT(LEFT(val, 2), '***@', SPLIT_PART(val, '@', 2))
            END
        """,
        "apply_to": ("BANK.CUSTOMERS", "EMAIL")
    },
    # Card number masking
    {
        "name": "BANK.MASK_CARD_NUMBER",
        "signature": "(val STRING)",
        "returns": "STRING",
        "body": """
            CASE
                WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'BANK_DB_ADMIN', 'BANK_COMPLIANCE_OFFICER')
                    THEN val
                ELSE CONCAT('XXXX-XXXX-XXXX-', RIGHT(val, 4))
            END
        """,
        "apply_to": ("BANK.CARDS", "CARD_NUMBER")
    },
    # CVV masking — nobody sees it except admin
    {
        "name": "BANK.MASK_CVV",
        "signature": "(val STRING)",
        "returns": "STRING",
        "body": """
            CASE
                WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'BANK_DB_ADMIN')
                    THEN val
                ELSE '***'
            END
        """,
        "apply_to": ("BANK.CARDS", "CVV")
    },
]


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    config = {
        "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
        "user":      os.getenv("SNOWFLAKE_USER"),
        "password":  os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database":  "TEST_BANK",
        "role":      "ACCOUNTADMIN",  # Need ACCOUNTADMIN for role management
    }
    config = {k: v for k, v in config.items() if v}

    print("🔗 Connecting to Snowflake as ACCOUNTADMIN...")
    conn = snowflake.connector.connect(**config)
    cursor = conn.cursor()
    print("✅ Connected!\n")

    try:
        # ── Step 1: Create Roles ───────────────────────────────────────────
        print("=" * 65)
        print("  STEP 1: CREATING ROLES")
        print("=" * 65)
        for role_name, role_info in ROLES.items():
            cursor.execute(f"CREATE ROLE IF NOT EXISTS {role_name}")
            cursor.execute(f"ALTER ROLE {role_name} SET COMMENT = '{role_info['comment']}'")
            print(f"  ✅ Created role: {role_name}")
        print()

        # ── Step 2: Build Role Hierarchy ───────────────────────────────────
        print("=" * 65)
        print("  STEP 2: BUILDING ROLE HIERARCHY")
        print("=" * 65)

        # Grant roles to their parent system roles
        for role_name, role_info in ROLES.items():
            parent = role_info["parent"]
            cursor.execute(f"GRANT ROLE {role_name} TO ROLE {parent}")
            print(f"  🔗 {role_name} → {parent}")

        # Set up role inheritance chains
        for child_role, parent_role in ROLE_INHERITANCE:
            cursor.execute(f"GRANT ROLE {child_role} TO ROLE {parent_role}")
            print(f"  🔗 {child_role} → {parent_role} (inheritance)")
        print()

        # ── Step 3: Create Additional Schemas ──────────────────────────────
        print("=" * 65)
        print("  STEP 3: CREATING ADDITIONAL SCHEMAS")
        print("=" * 65)
        for schema_info in ADDITIONAL_SCHEMAS:
            name = schema_info["name"]
            comment = schema_info["comment"]
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS TEST_BANK.{name} COMMENT = '{comment}'")
            print(f"  📁 Created schema: {name}")

            for role, privs in schema_info["grants"].items():
                cursor.execute(f"GRANT {privs} ON SCHEMA TEST_BANK.{name} TO ROLE {role}")
                print(f"     └── {privs} → {role}")
        print()

        # ── Step 4: Grant Database & Table Privileges ──────────────────────
        print("=" * 65)
        print("  STEP 4: GRANTING TABLE-LEVEL PRIVILEGES")
        print("=" * 65)
        for role_name, grants in DB_GRANTS.items():
            print(f"  📋 {role_name}:")
            for grant_sql in grants:
                try:
                    cursor.execute(grant_sql)
                    # Extract a short description from the SQL
                    print(f"     ✅ {grant_sql.split('GRANT ')[1][:70]}...")
                except Exception as e:
                    print(f"     ⚠️  {str(e)[:80]}")
        print()

        # ── Step 5: Grant Warehouse Access ─────────────────────────────────
        print("=" * 65)
        print("  STEP 5: GRANTING WAREHOUSE ACCESS")
        print("=" * 65)
        warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
        for role_name, privs in WAREHOUSE_GRANTS.items():
            try:
                cursor.execute(f"GRANT {privs} ON WAREHOUSE {warehouse} TO ROLE {role_name}")
                print(f"  ✅ {role_name}: {privs}")
            except Exception as e:
                print(f"  ⚠️  {role_name}: {str(e)[:80]}")
        print()

        # ── Step 6: Create Masking Policies ────────────────────────────────
        print("=" * 65)
        print("  STEP 6: CREATING DATA MASKING POLICIES")
        print("=" * 65)
        cursor.execute("USE SCHEMA TEST_BANK.BANK")

        for policy in MASKING_POLICIES:
            policy_name = policy["name"]
            table, column = policy["apply_to"]

            # Create the masking policy
            create_sql = f"""
                CREATE OR REPLACE MASKING POLICY {policy_name} AS
                {policy['signature']} RETURNS {policy['returns']} ->
                {policy['body']}
            """
            cursor.execute(create_sql)
            print(f"  🔒 Created policy: {policy_name}")

            # First unset any existing policy, then apply
            try:
                cursor.execute(f"ALTER TABLE {table} MODIFY COLUMN {column} UNSET MASKING POLICY")
            except Exception:
                pass  # No existing policy — that's fine

            cursor.execute(f"ALTER TABLE {table} MODIFY COLUMN {column} SET MASKING POLICY {policy_name}")
            print(f"     └── Applied to {table}.{column}")
        print()

        # ── Step 7: Grant current user all custom roles (for testing) ──────
        print("=" * 65)
        print("  STEP 7: GRANTING ROLES TO CURRENT USER (for testing)")
        print("=" * 65)
        current_user = os.getenv("SNOWFLAKE_USER")
        for role_name in ROLES:
            cursor.execute(f"GRANT ROLE {role_name} TO USER {current_user}")
            print(f"  👤 {role_name} → {current_user}")
        print()

        # ── Step 8: Verify — Show role hierarchy ──────────────────────────
        print("=" * 65)
        print("  📊 ROLE HIERARCHY VERIFICATION")
        print("=" * 65)
        cursor.execute("SHOW ROLES")
        results = cursor.fetchall()
        desc = [col[0] for col in cursor.description]
        name_idx = desc.index('name')
        comment_idx = desc.index('comment') if 'comment' in desc else None
        granted_roles_idx = desc.index('granted_roles') if 'granted_roles' in desc else None

        bank_roles = [r for r in results if str(r[name_idx]).startswith('BANK_')]
        for role in bank_roles:
            comment = role[comment_idx] if comment_idx else ''
            granted = role[granted_roles_idx] if granted_roles_idx else ''
            print(f"  {role[name_idx]:30s}  (inherits {granted} roles)  {comment[:50]}")

        print()
        print("=" * 65)
        print("  🎉 ROLE HIERARCHY SETUP COMPLETE!")
        print("=" * 65)
        print()
        print("  Quick test commands (run in Snowflake):")
        print("  ─────────────────────────────────────────")
        print("  USE ROLE BANK_TELLER;")
        print("  SELECT * FROM TEST_BANK.BANK.CUSTOMERS LIMIT 5;  -- PAN/Aadhar masked")
        print()
        print("  USE ROLE BANK_COMPLIANCE_OFFICER;")
        print("  SELECT * FROM TEST_BANK.BANK.CUSTOMERS LIMIT 5;  -- Full access")
        print()

        cursor.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    main()
