"""Generate and display the full SCIM bearer token for Azure AD.

After generating the token, automatically updates the SCIM_TOKEN_TRACKER
table with the current timestamp so the expiry tracker knows when the
token was last generated (not when the integration was created).
"""
import os
import sys
import snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

SCIM_INTEGRATION = os.getenv("SCIM_INTEGRATION_NAME", "AAD_SCIM_INTEGRATION")
DATABASE = os.getenv("SNOWFLAKE_DATABASE", "TEST_BANK")
SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
TRACKER_TABLE = f"{DATABASE}.{SCHEMA}.SCIM_TOKEN_TRACKER"
TOKEN_LIFESPAN_DAYS = 180

conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    role="ACCOUNTADMIN",
)

cur = conn.cursor()

# ── Step 1: Generate the SCIM token ───────────────────────────────────────
cur.execute(f"SELECT SYSTEM$GENERATE_SCIM_ACCESS_TOKEN('{SCIM_INTEGRATION}') AS TOKEN")
result = cur.fetchone()

print("\n" + "=" * 65)
print("  SCIM BEARER TOKEN")
print("  Use with:  Authorization: Bearer <token>")
print("=" * 65)
print()
print(result[0])
print()
print("=" * 65)
print(f"  SCIM Endpoint: https://{os.getenv('SNOWFLAKE_ACCOUNT')}.snowflakecomputing.com/scim/v2")
print("=" * 65)

# ── Step 2: Record generation timestamp in tracker table ──────────────────
print(f"\n📝 Recording token generation timestamp in {TRACKER_TABLE}...")
try:
    cur.execute(f"""
        MERGE INTO {TRACKER_TABLE} AS t
        USING (SELECT '{SCIM_INTEGRATION}' AS INTEGRATION_NAME) AS s
        ON t.INTEGRATION_NAME = s.INTEGRATION_NAME
        WHEN MATCHED THEN UPDATE SET
            TOKEN_GENERATED_AT  = CURRENT_TIMESTAMP(),
            TOKEN_EXPIRES_AT    = DATEADD(DAY, {TOKEN_LIFESPAN_DAYS}, CURRENT_TIMESTAMP()),
            TOKEN_GENERATED_VIA = 'gen_scim_token.py / SYSTEM$GENERATE_SCIM_ACCESS_TOKEN',
            DAYS_REMAINING      = {TOKEN_LIFESPAN_DAYS},
            STATUS              = 'HEALTHY',
            ALERT_10_SENT       = FALSE,
            ALERT_5_SENT        = FALSE,
            ALERT_3_SENT        = FALSE,
            ALERT_1_SENT        = FALSE,
            ALERT_0_SENT        = FALSE,
            UPDATED_AT          = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN INSERT
            (INTEGRATION_NAME, TOKEN_GENERATED_AT, TOKEN_EXPIRES_AT,
             TOKEN_GENERATED_VIA, DAYS_REMAINING, STATUS)
        VALUES
            ('{SCIM_INTEGRATION}', CURRENT_TIMESTAMP(),
             DATEADD(DAY, {TOKEN_LIFESPAN_DAYS}, CURRENT_TIMESTAMP()),
             'gen_scim_token.py / SYSTEM$GENERATE_SCIM_ACCESS_TOKEN',
             {TOKEN_LIFESPAN_DAYS}, 'HEALTHY')
    """)
    print(f"✅ Tracker updated — token expires in {TOKEN_LIFESPAN_DAYS} days from now")
    print(f"   Alert flags reset to FALSE")
except Exception as e:
    print(f"⚠️  Could not update tracker table: {e}")
    print(f"   (The tracker table may not exist yet — run sp_scim_token_tracker.py to deploy it)")

cur.close()
conn.close()
print("\n🔒 Connection closed.")
