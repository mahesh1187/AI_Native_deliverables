"""
Copy Role Grants Script
=========================
Copies ALL grants from a source role to a new target role.
Designed to run in any Snowflake environment.

Usage:
    python copy_role_grants.py

Configurable:
    SOURCE_ROLE  = "BANK_DB_ADMIN"    (existing role to copy from)
    TARGET_ROLE  = "TG_BANK_ADMIN"    (new role to create and grant to)
"""

import os
import sys
import snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

# ─── Configuration ─────────────────────────────────────────────────────────────
SOURCE_ROLE = "BANK_DB_ADMIN"
TARGET_ROLE = "TG_BANK_ADMIN"


def get_connection():
    """Connect to Snowflake as ACCOUNTADMIN."""
    config = {
        "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
        "user":      os.getenv("SNOWFLAKE_USER"),
        "password":  os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database":  os.getenv("SNOWFLAKE_DATABASE", "TEST_BANK"),
        "role":      "ACCOUNTADMIN",
    }
    return snowflake.connector.connect(**{k: v for k, v in config.items() if v})


def get_grants_for_role(cursor, role_name):
    """Retrieve all grants assigned TO a role (privileges on objects)."""
    cursor.execute(f"SHOW GRANTS TO ROLE {role_name}")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    grants = [dict(zip(columns, row)) for row in rows]
    return grants


def get_roles_granted_to_role(cursor, role_name):
    """Retrieve all roles granted TO a role (role inheritance)."""
    cursor.execute(f"SHOW GRANTS OF ROLE {role_name}")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def build_grant_sql(grant, target_role):
    """
    Build a GRANT SQL statement from a grant record.
    
    SHOW GRANTS TO ROLE returns columns like:
      privilege, granted_on, name, granted_to, grantee_name, grant_option, granted_by
    """
    privilege = grant.get("privilege", "")
    granted_on = grant.get("granted_on", "")
    obj_name = grant.get("name", "")

    # Skip USAGE on the role itself and OWNERSHIP grants (can't be copied)
    if privilege == "OWNERSHIP":
        return None, "OWNERSHIP cannot be copied — skipped"

    # Skip if granted_on is ROLE (these are role-to-role grants, handled separately)
    if granted_on == "ROLE":
        return None, "Role-to-role grant — handled via inheritance"

    # Build the GRANT statement
    grant_option = ""
    if grant.get("grant_option", "false") == "true":
        grant_option = " WITH GRANT OPTION"

    sql = f"GRANT {privilege} ON {granted_on} {obj_name} TO ROLE {target_role}{grant_option}"
    return sql, None


def main():
    print("🔗 Connecting to Snowflake...")
    conn = get_connection()
    cursor = conn.cursor()
    print("✅ Connected!\n")

    try:
        # ── Step 1: Verify source role exists ──────────────────────────────
        print(f"📋 Source Role: {SOURCE_ROLE}")
        print(f"🎯 Target Role: {TARGET_ROLE}")
        print("=" * 70)

        # ── Step 2: Fetch all grants from source role ──────────────────────
        print(f"\n📥 Fetching grants from {SOURCE_ROLE}...")
        grants = get_grants_for_role(cursor, SOURCE_ROLE)
        print(f"   Found {len(grants)} grant(s)\n")

        if not grants:
            print(f"⚠️  No grants found for role {SOURCE_ROLE}. Exiting.")
            return

        # ── Step 3: Display source grants ──────────────────────────────────
        print("=" * 70)
        print(f"  GRANTS ON {SOURCE_ROLE} (source)")
        print("=" * 70)
        print(f"  {'#':<4} {'PRIVILEGE':<22} {'GRANTED_ON':<16} {'OBJECT NAME'}")
        print(f"  {'─'*4} {'─'*22} {'─'*16} {'─'*40}")

        for i, g in enumerate(grants, 1):
            priv = g.get("privilege", "?")
            on_type = g.get("granted_on", "?")
            name = g.get("name", "?")
            grant_opt = " [+GRANT]" if g.get("grant_option") == "true" else ""
            print(f"  {i:<4} {priv:<22} {on_type:<16} {name}{grant_opt}")
        print()

        # ── Step 4: Fetch role inheritance ─────────────────────────────────
        print(f"📥 Fetching role hierarchy for {SOURCE_ROLE}...")
        cursor.execute(f"SHOW GRANTS TO ROLE {SOURCE_ROLE}")
        all_grants = get_grants_for_role(cursor, SOURCE_ROLE)
        role_grants = [g for g in all_grants if g.get("granted_on") == "ROLE"]

        if role_grants:
            print(f"   Found {len(role_grants)} inherited role(s):")
            for rg in role_grants:
                print(f"     🔗 {rg.get('name', '?')}")
        else:
            print("   No inherited roles found.")
        print()

        # ── Step 5: Create target role ─────────────────────────────────────
        print(f"🔨 Creating target role: {TARGET_ROLE}...")
        cursor.execute(f"""
            CREATE ROLE IF NOT EXISTS {TARGET_ROLE}
            COMMENT = 'Cloned from {SOURCE_ROLE} — all grants copied'
        """)
        print(f"   ✅ Role {TARGET_ROLE} created\n")

        # ── Step 6: Copy all grants ────────────────────────────────────────
        print("=" * 70)
        print(f"  COPYING GRANTS → {TARGET_ROLE}")
        print("=" * 70)

        success_count = 0
        skip_count = 0
        fail_count = 0
        failed_grants = []

        for i, grant in enumerate(grants, 1):
            sql, skip_reason = build_grant_sql(grant, TARGET_ROLE)

            if skip_reason:
                priv = grant.get("privilege", "?")
                on_type = grant.get("granted_on", "?")
                name = grant.get("name", "?")
                print(f"  ⏭️  #{i} SKIP: {priv} ON {on_type} {name}")
                print(f"       Reason: {skip_reason}")
                skip_count += 1
                continue

            try:
                cursor.execute(sql)
                print(f"  ✅ #{i} {sql}")
                success_count += 1
            except Exception as e:
                error_msg = str(e).split('\n')[0][:100]
                print(f"  ❌ #{i} FAILED: {sql}")
                print(f"       Error: {error_msg}")
                failed_grants.append({"sql": sql, "error": error_msg})
                fail_count += 1

        # ── Step 7: Copy role inheritance ──────────────────────────────────
        if role_grants:
            print(f"\n  📎 Copying role inheritance...")
            for rg in role_grants:
                role_name = rg.get("name", "")
                if role_name:
                    try:
                        sql = f"GRANT ROLE {role_name} TO ROLE {TARGET_ROLE}"
                        cursor.execute(sql)
                        print(f"  ✅ {sql}")
                        success_count += 1
                    except Exception as e:
                        error_msg = str(e).split('\n')[0][:100]
                        print(f"  ❌ FAILED: GRANT ROLE {role_name} TO ROLE {TARGET_ROLE}")
                        print(f"       Error: {error_msg}")
                        failed_grants.append({"sql": sql, "error": error_msg})
                        fail_count += 1

        # ── Step 8: Grant to parent role (same as source) ──────────────────
        print(f"\n  📎 Granting {TARGET_ROLE} to SYSADMIN (matching source hierarchy)...")
        try:
            cursor.execute(f"GRANT ROLE {TARGET_ROLE} TO ROLE SYSADMIN")
            print(f"  ✅ GRANT ROLE {TARGET_ROLE} TO ROLE SYSADMIN")
            success_count += 1
        except Exception as e:
            print(f"  ⚠️  Could not grant to SYSADMIN: {e}")

        # ── Step 9: Grant to current user for testing ──────────────────────
        current_user = os.getenv("SNOWFLAKE_USER")
        if current_user:
            cursor.execute(f"GRANT ROLE {TARGET_ROLE} TO USER {current_user}")
            print(f"  ✅ GRANT ROLE {TARGET_ROLE} TO USER {current_user}")

        # ── Step 10: Verification ──────────────────────────────────────────
        print("\n" + "=" * 70)
        print("  📊 VERIFICATION — Comparing Grants")
        print("=" * 70)

        source_grants = get_grants_for_role(cursor, SOURCE_ROLE)
        target_grants = get_grants_for_role(cursor, TARGET_ROLE)

        # Build comparable sets (privilege + granted_on + name)
        def grant_key(g):
            return (g.get("privilege", ""), g.get("granted_on", ""), g.get("name", ""))

        source_set = {grant_key(g) for g in source_grants if g.get("privilege") != "OWNERSHIP"}
        target_set = {grant_key(g) for g in target_grants if g.get("privilege") != "OWNERSHIP"}

        matched = source_set & target_set
        missing = source_set - target_set
        extra = target_set - source_set

        print(f"\n  {SOURCE_ROLE}: {len(source_set)} grants (excl. OWNERSHIP)")
        print(f"  {TARGET_ROLE}: {len(target_set)} grants (excl. OWNERSHIP)")
        print(f"\n  ✅ Matched:  {len(matched)}")
        print(f"  ❌ Missing:  {len(missing)}")
        print(f"  ➕ Extra:    {len(extra)}")

        if missing:
            print(f"\n  ⚠️  Grants in {SOURCE_ROLE} but NOT in {TARGET_ROLE}:")
            for priv, on_type, name in sorted(missing):
                print(f"     • {priv} ON {on_type} {name}")

        if extra:
            print(f"\n  ℹ️  Grants in {TARGET_ROLE} but NOT in {SOURCE_ROLE}:")
            for priv, on_type, name in sorted(extra):
                print(f"     • {priv} ON {on_type} {name}")

        # ── Summary ───────────────────────────────────────────────────────
        print("\n" + "=" * 70)
        print("  📋 SUMMARY")
        print("=" * 70)
        print(f"  ✅ Successful:  {success_count}")
        print(f"  ⏭️  Skipped:     {skip_count}")
        print(f"  ❌ Failed:      {fail_count}")

        match_pct = (len(matched) / len(source_set) * 100) if source_set else 100
        print(f"\n  🎯 Grant match: {match_pct:.0f}%")

        if match_pct == 100 and fail_count == 0:
            print(f"\n  🎉 SUCCESS! {TARGET_ROLE} is a complete clone of {SOURCE_ROLE}")
        elif fail_count > 0:
            print(f"\n  ⚠️  Some grants failed. Review errors above.")
        print("=" * 70)

        if failed_grants:
            print("\n  Failed grant statements (for manual retry):")
            for fg in failed_grants:
                print(f"    {fg['sql']};")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        conn.close()
        print("\n🔒 Connection closed.")


if __name__ == "__main__":
    main()
