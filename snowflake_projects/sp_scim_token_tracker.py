"""
Snowflake Stored Procedure — SCIM Token Expiry Tracker (Python)
=================================================================
Deploys a complete in-Snowflake solution to track SCIM token expiry:

    1. Notification Integration  — for sending email via SYSTEM$SEND_EMAIL
    2. Tracking Table            — stores token state & alert history
    3. Stored Procedure (Python) — checks expiry, resolves user email, sends alerts
    4. Scheduled Task            — runs the procedure daily at 8 AM UTC

The stored procedure automatically resolves the calling user's email
address from Snowflake and uses it as the notification recipient.

Prerequisites:
    • ACCOUNTADMIN role
    • Your Snowflake user must have an email address set:
        ALTER USER <username> SET EMAIL = 'you@example.com';
    • An existing SCIM integration (e.g. AAD_SCIM_INTEGRATION)

Usage:
    python sp_scim_token_tracker.py                # Deploy everything
    python sp_scim_token_tracker.py --dry-run      # Preview SQL only
    python sp_scim_token_tracker.py --teardown     # Remove all objects
    python sp_scim_token_tracker.py --test-run     # Deploy + execute immediately
"""

import os
import sys
import argparse
import snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


# ─── Configuration ─────────────────────────────────────────────────────────────

SNOWFLAKE_CONFIG = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
    "user":      os.getenv("SNOWFLAKE_USER"),
    "password":  os.getenv("SNOWFLAKE_PASSWORD"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database":  os.getenv("SNOWFLAKE_DATABASE", "TEST_BANK"),
    "schema":    os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    "role":      os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
}

# Customizable names
SCIM_INTEGRATION_NAME   = os.getenv("SCIM_INTEGRATION_NAME", "AAD_SCIM_INTEGRATION")
NOTIFICATION_INTEG_NAME = "SCIM_EMAIL_NOTIFICATION"
TRACKER_TABLE           = "SCIM_TOKEN_TRACKER"
ALERT_HISTORY_TABLE     = "SCIM_TOKEN_ALERT_HISTORY"
PROCEDURE_NAME          = "SP_CHECK_SCIM_TOKEN_EXPIRY"
TASK_NAME               = "TASK_SCIM_TOKEN_MONITOR"
WAREHOUSE               = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
DATABASE                = SNOWFLAKE_CONFIG["database"]
SCHEMA                  = SNOWFLAKE_CONFIG["schema"]
FULL_TABLE              = f"{DATABASE}.{SCHEMA}.{TRACKER_TABLE}"
FULL_HISTORY            = f"{DATABASE}.{SCHEMA}.{ALERT_HISTORY_TABLE}"
FULL_PROC               = f"{DATABASE}.{SCHEMA}.{PROCEDURE_NAME}"
FULL_TASK               = f"{DATABASE}.{SCHEMA}.{TASK_NAME}"


# ─── SQL Definitions ──────────────────────────────────────────────────────────

SQL_STEPS = []


def step(description, sql):
    """Register a SQL step."""
    SQL_STEPS.append({"description": description, "sql": sql.strip()})


# ── Step 1: Email Notification Integration ─────────────────────────────────
step(
    "Create email notification integration",
    f"""
CREATE NOTIFICATION INTEGRATION IF NOT EXISTS {NOTIFICATION_INTEG_NAME}
    TYPE = EMAIL
    ENABLED = TRUE
    COMMENT = 'Email notifications for SCIM token expiry alerts'
"""
)

# ── Step 2: Tracking Table ─────────────────────────────────────────────────
step(
    f"Create tracking table {FULL_TABLE}",
    f"""
CREATE TABLE IF NOT EXISTS {FULL_TABLE} (
    INTEGRATION_NAME     VARCHAR(256)   NOT NULL,
    TOKEN_GENERATED_AT   TIMESTAMP_NTZ,
    TOKEN_EXPIRES_AT     TIMESTAMP_NTZ,
    TOKEN_LIFESPAN_DAYS  INT            DEFAULT 180,
    TOKEN_GENERATED_VIA  VARCHAR(500)   DEFAULT 'SYSTEM$GENERATE_SCIM_ACCESS_TOKEN',
    LAST_CHECK_AT        TIMESTAMP_NTZ,
    DAYS_REMAINING       INT,
    ALERT_10_SENT        BOOLEAN        DEFAULT FALSE,
    ALERT_5_SENT         BOOLEAN        DEFAULT FALSE,
    ALERT_3_SENT         BOOLEAN        DEFAULT FALSE,
    ALERT_1_SENT         BOOLEAN        DEFAULT FALSE,
    ALERT_0_SENT         BOOLEAN        DEFAULT FALSE,
    LAST_ALERT_SENT_AT   TIMESTAMP_NTZ,
    LAST_ALERT_EMAIL     VARCHAR(500),
    STATUS               VARCHAR(20)    DEFAULT 'UNKNOWN',
    CREATED_AT           TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT           TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT PK_SCIM_TRACKER PRIMARY KEY (INTEGRATION_NAME)
)
"""
)

# ── Step 3: Alert History Table ────────────────────────────────────────────
step(
    f"Create alert history table {FULL_HISTORY}",
    f"""
CREATE TABLE IF NOT EXISTS {FULL_HISTORY} (
    ALERT_ID             INT AUTOINCREMENT,
    INTEGRATION_NAME     VARCHAR(256)   NOT NULL,
    ALERT_TYPE           VARCHAR(50),
    DAYS_REMAINING       INT,
    USER_EMAIL           VARCHAR(500),
    ALERT_SENT_AT        TIMESTAMP_NTZ  DEFAULT CURRENT_TIMESTAMP(),
    STATUS               VARCHAR(20)    DEFAULT 'SENT',

    CONSTRAINT PK_ALERT_HISTORY PRIMARY KEY (ALERT_ID)
)
"""
)

# ── Step 4: Python Stored Procedure ───────────────────────────────────────
#
# The procedure accepts an optional EMAIL_OVERRIDE parameter:
#   - If provided → sends alerts to that email address
#   - If empty/omitted → resolves the calling user's email from SHOW USERS
#
SP_BODY = f"""
CREATE OR REPLACE PROCEDURE {FULL_PROC}(EMAIL_OVERRIDE VARCHAR DEFAULT '')
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'check_scim_token_expiry'
EXECUTE AS CALLER
AS
$$
from datetime import datetime, timedelta

def check_scim_token_expiry(session, email_override=''):
    INTEGRATION_NAME    = '{SCIM_INTEGRATION_NAME}'
    TRACKER_TABLE       = '{FULL_TABLE}'
    ALERT_HISTORY_TABLE = '{FULL_HISTORY}'
    NOTIFICATION_INTEG  = '{NOTIFICATION_INTEG_NAME}'
    TOKEN_LIFESPAN_DAYS = 180
    ALERT_THRESHOLDS    = [10, 5, 3, 1, 0]

    # ── Step 1: Resolve recipient email ────────────────────────
    current_user = session.sql("SELECT CURRENT_USER()").collect()[0][0]

    # Use the provided email if given, otherwise look up user's email
    if email_override and email_override.strip():
        user_email = email_override.strip()
    else:
        session.sql(f"SHOW USERS LIKE '{{current_user}}'").collect()
        user_rows = session.sql(
            "SELECT \\"email\\" FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))"
        ).collect()

        user_email = ''
        if user_rows and user_rows[0][0]:
            user_email = user_rows[0][0].strip()

    if not user_email:
        return (
            f"ERROR: No email provided and no email set for user '{{current_user}}'. "
            f"Either pass an email: CALL {FULL_PROC}('you@example.com') "
            f"or set it: ALTER USER {{current_user}} SET EMAIL = 'you@example.com'"
        )

    # ── Step 2: Get token generation date (when token was last generated) ──
    # The token age is tracked from TOKEN_GENERATED_AT — the timestamp
    # when SYSTEM$GENERATE_SCIM_ACCESS_TOKEN() was last executed,
    # NOT the integration creation date.
    existing = session.sql(
        f"SELECT TOKEN_GENERATED_AT FROM {{TRACKER_TABLE}} "
        f"WHERE INTEGRATION_NAME = '{{INTEGRATION_NAME}}'"
    ).collect()

    token_generated = None

    if existing and existing[0][0]:
        token_generated = existing[0][0]
    else:
        # No generation date recorded — check if the row exists at all
        row_exists = session.sql(
            f"SELECT COUNT(*) AS CNT FROM {{TRACKER_TABLE}} "
            f"WHERE INTEGRATION_NAME = '{{INTEGRATION_NAME}}'"
        ).collect()

        if not row_exists or row_exists[0][0] == 0:
            # Seed the row
            session.sql(
                f"INSERT INTO {{TRACKER_TABLE}} (INTEGRATION_NAME) "
                f"VALUES ('{{INTEGRATION_NAME}}')"
            ).collect()

        return (
            f"WARNING: No token generation date recorded for '{{INTEGRATION_NAME}}'. "
            f"Please generate a token first using: "
            f"SELECT SYSTEM$GENERATE_SCIM_ACCESS_TOKEN('{{INTEGRATION_NAME}}'); "
            f"Then record it: UPDATE {{TRACKER_TABLE}} SET "
            f"TOKEN_GENERATED_AT = CURRENT_TIMESTAMP(), "
            f"TOKEN_EXPIRES_AT = DATEADD(DAY, {{TOKEN_LIFESPAN_DAYS}}, CURRENT_TIMESTAMP()), "
            f"TOKEN_GENERATED_VIA = 'SYSTEM$GENERATE_SCIM_ACCESS_TOKEN', "
            f"STATUS = 'HEALTHY' "
            f"WHERE INTEGRATION_NAME = '{{INTEGRATION_NAME}}';"
        )

    # ── Step 3: Calculate days remaining from generation date ──
    if isinstance(token_generated, str):
        token_generated = datetime.fromisoformat(str(token_generated).replace('Z', '+00:00'))

    # Make naive for comparison
    if hasattr(token_generated, 'tzinfo') and token_generated.tzinfo is not None:
        token_generated = token_generated.replace(tzinfo=None)

    expires_at = token_generated + timedelta(days=TOKEN_LIFESPAN_DAYS)
    now = datetime.now()
    days_remaining = (expires_at - now).days

    # Determine status
    if days_remaining <= 0:
        status = 'EXPIRED'
    elif days_remaining <= 3:
        status = 'CRITICAL'
    elif days_remaining <= 10:
        status = 'WARNING'
    else:
        status = 'HEALTHY'

    # Update tracker
    session.sql(
        f"UPDATE {{TRACKER_TABLE}} SET "
        f"LAST_CHECK_AT = CURRENT_TIMESTAMP(), "
        f"TOKEN_EXPIRES_AT = '{{expires_at}}'::TIMESTAMP_NTZ, "
        f"DAYS_REMAINING = {{days_remaining}}, "
        f"STATUS = '{{status}}', "
        f"UPDATED_AT = CURRENT_TIMESTAMP() "
        f"WHERE INTEGRATION_NAME = '{{INTEGRATION_NAME}}'"
    ).collect()

    # ── Step 4: Check if alert is needed ───────────────────────
    flags = session.sql(
        f"SELECT ALERT_10_SENT, ALERT_5_SENT, ALERT_3_SENT, "
        f"ALERT_1_SENT, ALERT_0_SENT "
        f"FROM {{TRACKER_TABLE}} "
        f"WHERE INTEGRATION_NAME = '{{INTEGRATION_NAME}}'"
    ).collect()

    if not flags:
        return "ERROR: Tracker row not found"

    alert_flags = {{
        10: flags[0][0],
        5:  flags[0][1],
        3:  flags[0][2],
        1:  flags[0][3],
        0:  flags[0][4],
    }}

    alert_sent = False
    alert_threshold = None

    for threshold in ALERT_THRESHOLDS:
        if days_remaining <= threshold and not alert_flags.get(threshold, False):

            # ── Build styled HTML email ────────────────────────
            if days_remaining <= 0:
                urgency = 'EXPIRED'
                urgency_color = '#dc2626'
                headline = 'Your SCIM token has EXPIRED!'
            elif days_remaining <= 3:
                urgency = 'CRITICAL'
                urgency_color = '#ea580c'
                headline = f'Token expires in {{days_remaining}} day(s)!'
            else:
                urgency = 'WARNING'
                urgency_color = '#ca8a04'
                headline = f'Token expires in {{days_remaining}} days'

            generated_str = token_generated.strftime('%Y-%m-%d %H:%M')
            expires_str = expires_at.strftime('%Y-%m-%d')
            days_display = str(days_remaining) if days_remaining > 0 else 'EXPIRED'

            subject = f'[{{urgency}}] Snowflake SCIM Token - {{headline}}'

            email_body = f'''<div style="font-family:Segoe UI,Arial,sans-serif;max-width:600px;margin:0 auto;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
<div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);padding:24px 32px;color:white;">
<h1 style="margin:0;font-size:20px;">Snowflake SCIM Token Alert</h1>
<p style="margin:6px 0 0;opacity:0.85;font-size:14px;">Automated monitoring via Stored Procedure</p></div>
<div style="padding:28px 32px;">
<div style="display:inline-block;background:{{urgency_color}};color:white;padding:6px 16px;border-radius:20px;font-size:13px;font-weight:600;margin-bottom:16px;">{{urgency}}</div>
<h2 style="margin:0 0 16px;color:#1f2937;font-size:18px;">{{headline}}</h2>
<table style="width:100%;border-collapse:collapse;margin:16px 0;">
<tr style="border-bottom:1px solid #f3f4f6;"><td style="padding:10px 0;color:#6b7280;">Integration</td><td style="padding:10px 0;font-weight:600;">{{INTEGRATION_NAME}}</td></tr>
<tr style="border-bottom:1px solid #f3f4f6;"><td style="padding:10px 0;color:#6b7280;">Token Generated</td><td style="padding:10px 0;font-weight:600;">{{generated_str}}</td></tr>
<tr style="border-bottom:1px solid #f3f4f6;"><td style="padding:10px 0;color:#6b7280;">Token Expires</td><td style="padding:10px 0;font-weight:600;color:{{urgency_color}};">{{expires_str}}</td></tr>
<tr><td style="padding:10px 0;color:#6b7280;">Days Remaining</td><td style="padding:10px 0;font-weight:600;color:{{urgency_color}};">{{days_display}}</td></tr>
<tr style="border-top:1px solid #f3f4f6;"><td style="padding:10px 0;color:#6b7280;">Notified User</td><td style="padding:10px 0;font-weight:600;">{{current_user}} ({{user_email}})</td></tr>
</table>
<div style="background:#f0f9ff;border-left:4px solid #2563eb;padding:16px 20px;border-radius:0 8px 8px 0;margin:20px 0;">
<p style="margin:0 0 8px;font-weight:600;color:#1e40af;font-size:14px;">How to renew:</p>
<ol style="margin:0;padding-left:20px;color:#374151;font-size:13px;line-height:1.8;">
<li>Run: <code>python create_scim_integration.py</code></li>
<li>Copy the new bearer token</li>
<li>Update Azure AD Enterprise App Provisioning</li>
<li>Reset tracker flags in Snowflake</li></ol></div>
</div>
<div style="background:#f9fafb;padding:16px 32px;border-top:1px solid #e5e7eb;font-size:12px;color:#9ca3af;">Sent by SP_CHECK_SCIM_TOKEN_EXPIRY to {{user_email}}</div></div>'''

            # ── Send email ─────────────────────────────────────
            try:
                escaped_subject = subject.replace("'", "''")
                escaped_body = email_body.replace("'", "''")

                session.sql(
                    f"CALL SYSTEM$SEND_EMAIL("
                    f"'{{NOTIFICATION_INTEG}}', "
                    f"'{{user_email}}', "
                    f"'{{escaped_subject}}', "
                    f"'{{escaped_body}}', "
                    f"'text/html')"
                ).collect()

                # Update alert flag
                flag_col = f'ALERT_{{threshold}}_SENT'
                session.sql(
                    f"UPDATE {{TRACKER_TABLE}} SET "
                    f"{{flag_col}} = TRUE, "
                    f"LAST_ALERT_SENT_AT = CURRENT_TIMESTAMP(), "
                    f"LAST_ALERT_EMAIL = '{{user_email}}', "
                    f"UPDATED_AT = CURRENT_TIMESTAMP() "
                    f"WHERE INTEGRATION_NAME = '{{INTEGRATION_NAME}}'"
                ).collect()

                # Log to alert history
                session.sql(
                    f"INSERT INTO {{ALERT_HISTORY_TABLE}} "
                    f"(INTEGRATION_NAME, ALERT_TYPE, DAYS_REMAINING, USER_EMAIL) "
                    f"VALUES ('{{INTEGRATION_NAME}}', '{{threshold}}_DAY_ALERT', "
                    f"{{days_remaining}}, '{{user_email}}')"
                ).collect()

                alert_sent = True
                alert_threshold = threshold

            except Exception as e:
                # Log failed alert
                session.sql(
                    f"INSERT INTO {{ALERT_HISTORY_TABLE}} "
                    f"(INTEGRATION_NAME, ALERT_TYPE, DAYS_REMAINING, USER_EMAIL, STATUS) "
                    f"VALUES ('{{INTEGRATION_NAME}}', '{{threshold}}_DAY_ALERT', "
                    f"{{days_remaining}}, '{{user_email}}', 'FAILED')"
                ).collect()
                return f"ERROR sending email to {{user_email}}: {{str(e)}}"

            break  # One alert per run

    # ── Return summary ─────────────────────────────────────────
    alert_msg = (
        f' | Alert sent to {{user_email}} for {{alert_threshold}}-day threshold'
        if alert_sent else ' | No alert needed'
    )
    return (
        f'Status: {{status}} | Days remaining: {{days_remaining}} | '
        f'Generated: {{token_generated.strftime("%Y-%m-%d %H:%M")}} | '
        f'Expires: {{expires_at.strftime("%Y-%m-%d")}} | '
        f'User: {{current_user}} ({{user_email}}){{alert_msg}}'
    )
$$
"""

step(f"Create Python stored procedure {FULL_PROC}", SP_BODY)


# ── Step 5: Scheduled Task (daily at 8 AM UTC) ────────────────────────────
step(
    f"Create scheduled task {FULL_TASK}",
    f"""
CREATE OR REPLACE TASK {FULL_TASK}
    WAREHOUSE = {WAREHOUSE}
    SCHEDULE  = 'USING CRON 0 8 * * * UTC'
    COMMENT   = 'Daily SCIM token expiry check — sends email to the executing user'
AS
    CALL {FULL_PROC}('')
"""
)

# ── Step 6: Resume (activate) the task ─────────────────────────────────────
step(
    f"Activate task {FULL_TASK}",
    f"ALTER TASK {FULL_TASK} RESUME"
)

# ── Step 7: Seed the tracker ──────────────────────────────────────────────
step(
    "Seed tracker table with current integration",
    f"""
MERGE INTO {FULL_TABLE} AS target
USING (SELECT '{SCIM_INTEGRATION_NAME}' AS INTEGRATION_NAME) AS source
ON target.INTEGRATION_NAME = source.INTEGRATION_NAME
WHEN NOT MATCHED THEN
    INSERT (INTEGRATION_NAME) VALUES (source.INTEGRATION_NAME)
"""
)


# ─── Teardown SQL ──────────────────────────────────────────────────────────

TEARDOWN_STEPS = [
    (f"Suspend task",      f"ALTER TASK IF EXISTS {FULL_TASK} SUSPEND"),
    (f"Drop task",         f"DROP TASK IF EXISTS {FULL_TASK}"),
    (f"Drop procedure",    f"DROP PROCEDURE IF EXISTS {FULL_PROC}(VARCHAR)"),
    (f"Drop tracker table",f"DROP TABLE IF EXISTS {FULL_TABLE}"),
    (f"Drop history table",f"DROP TABLE IF EXISTS {FULL_HISTORY}"),
    (f"Drop notification", f"DROP NOTIFICATION INTEGRATION IF EXISTS {NOTIFICATION_INTEG_NAME}"),
]


# ─── Execution Engine ─────────────────────────────────────────────────────

def get_connection():
    """Create a Snowflake connection."""
    config = {k: v for k, v in SNOWFLAKE_CONFIG.items() if v and v != f"your_{k}"}
    if not all(k in config for k in ("account", "user", "password")):
        print("❌ Missing Snowflake credentials in .env")
        sys.exit(1)
    try:
        conn = snowflake.connector.connect(**config)
        print("✅ Connected to Snowflake")
        return conn
    except snowflake.connector.errors.DatabaseError as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)


def run_sql(conn, sql, description, dry_run=False):
    """Execute a SQL statement with logging."""
    print(f"\n{'🔍' if dry_run else '▶️ '} {description}")
    if dry_run:
        display = sql.strip()
        if len(display) > 300:
            display = display[:300] + "\n   ... (truncated)"
        print(f"   [DRY RUN] SQL:\n   {display}")
        return None
    else:
        short = sql.strip()[:120]
        print(f"   SQL: {short}{'...' if len(sql.strip()) > 120 else ''}")
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            result = cursor.fetchall()
            print("   ✅ Done")
            return result
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
        finally:
            cursor.close()


def deploy(conn, dry_run=False):
    """Deploy all objects to Snowflake."""
    print("\n" + "🔷" * 30)
    print("  DEPLOY SCIM TOKEN TRACKER — PYTHON STORED PROCEDURE")
    print("🔷" * 30)

    if dry_run:
        print("\n   ⚡ DRY RUN MODE — no changes will be made\n")

    for i, step_def in enumerate(SQL_STEPS, 1):
        print(f"\n{'─' * 65}")
        print(f"  STEP {i}/{len(SQL_STEPS)}")
        run_sql(conn, step_def["sql"], step_def["description"], dry_run=dry_run)

    print("\n" + "=" * 65)
    if dry_run:
        print("  📝 DRY RUN COMPLETE — No changes were made")
    else:
        print("  ✅ DEPLOYMENT COMPLETE")
        print("=" * 65)
        print(f"""
   Objects created:
   ─────────────────
   1. Notification:  {NOTIFICATION_INTEG_NAME}
   2. Table:         {FULL_TABLE}
   3. History Table: {FULL_HISTORY}
   4. Procedure:     {FULL_PROC}(EMAIL_OVERRIDE)  [LANGUAGE = PYTHON]
   5. Task:          {FULL_TASK} (daily at 8:00 AM UTC)

   📧 Email resolution:
   • Pass an email:  CALL {FULL_PROC}('admin@example.com');
   • Or omit it:     CALL {FULL_PROC}();  -- uses your Snowflake user email
   • To set your Snowflake email:
       ALTER USER <username> SET EMAIL = 'you@example.com';

   Useful queries:
   ───────────────
   -- Check current status
   SELECT * FROM {FULL_TABLE};

   -- View alert history
   SELECT * FROM {FULL_HISTORY} ORDER BY ALERT_SENT_AT DESC;

   -- Run with a specific email
   CALL {FULL_PROC}('your_email@example.com');

   -- Run using your Snowflake user email (default)
   CALL {FULL_PROC}();

   -- Check task status
   SHOW TASKS LIKE '{TASK_NAME}';

    -- After generating a new token, record it and reset alert flags:
    -- Step 1: Generate the token
    SELECT SYSTEM$GENERATE_SCIM_ACCESS_TOKEN('{SCIM_INTEGRATION_NAME}');

    -- Step 2: Update the tracker with the generation timestamp
    UPDATE {FULL_TABLE}
    SET ALERT_10_SENT = FALSE, ALERT_5_SENT = FALSE,
        ALERT_3_SENT = FALSE, ALERT_1_SENT = FALSE,
        ALERT_0_SENT = FALSE,
        TOKEN_GENERATED_AT = CURRENT_TIMESTAMP(),
        TOKEN_GENERATED_VIA = 'SYSTEM$GENERATE_SCIM_ACCESS_TOKEN',
        TOKEN_EXPIRES_AT = DATEADD(DAY, 180, CURRENT_TIMESTAMP()),
        STATUS = 'HEALTHY'
    WHERE INTEGRATION_NAME = '{SCIM_INTEGRATION_NAME}';
""")
    print("=" * 65)


def teardown(conn, dry_run=False):
    """Remove all deployed objects."""
    print("\n" + "🔴" * 30)
    print("  TEARDOWN SCIM TOKEN TRACKER")
    print("🔴" * 30)

    if dry_run:
        print("\n   ⚡ DRY RUN MODE — no changes will be made\n")

    for desc, sql in TEARDOWN_STEPS:
        run_sql(conn, sql, desc, dry_run=dry_run)

    print("\n" + "=" * 65)
    if dry_run:
        print("  📝 DRY RUN COMPLETE — No changes were made")
    else:
        print("  🗑️  TEARDOWN COMPLETE — All objects removed")
    print("=" * 65)


def test_run(conn):
    """Execute the stored procedure immediately and display results."""
    print("\n" + "=" * 65)
    print("  TEST RUN — Executing Python stored procedure")
    print("=" * 65)

    cursor = conn.cursor()
    try:
        cursor.execute(f"CALL {FULL_PROC}()")
        result = cursor.fetchone()
        print(f"\n   📋 Result: {result[0]}")
    except Exception as e:
        print(f"\n   ❌ Error: {e}")
    finally:
        cursor.close()

    # Show tracker table contents
    print(f"\n   📊 Tracker table:")
    cursor = conn.cursor(snowflake.connector.DictCursor)
    try:
        cursor.execute(f"SELECT * FROM {FULL_TABLE}")
        rows = cursor.fetchall()
        for row in rows:
            print(f"   {'─' * 50}")
            for key, val in row.items():
                print(f"   {key:<25} {val}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    finally:
        cursor.close()

    print("\n" + "=" * 65)


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Deploy SCIM Token Expiry Tracker (Python SP + Task) to Snowflake"
    )
    parser.add_argument("--dry-run",   action="store_true", help="Preview SQL without executing")
    parser.add_argument("--teardown",  action="store_true", help="Remove all deployed objects")
    parser.add_argument("--test-run",  action="store_true", help="Deploy and execute the SP immediately")
    args = parser.parse_args()

    conn = get_connection()

    try:
        if args.teardown:
            teardown(conn)
        elif args.dry_run:
            deploy(conn, dry_run=True)
        else:
            deploy(conn)
            if args.test_run:
                test_run(conn)
    finally:
        conn.close()
        print("\n🔒 Connection closed.")


if __name__ == "__main__":
    main()
