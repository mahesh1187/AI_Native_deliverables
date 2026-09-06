"""Test the SCIM token monitor email by simulating near-expiry, then reset."""
import os, sys, snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

conn = snowflake.connector.connect(
    account=os.getenv('SNOWFLAKE_ACCOUNT'),
    user=os.getenv('SNOWFLAKE_USER'),
    password=os.getenv('SNOWFLAKE_PASSWORD'),
    role='ACCOUNTADMIN',
    database='TEST_BANK',
    schema='PUBLIC',
)
cur = conn.cursor(snowflake.connector.DictCursor)

print("\n" + "=" * 65)
print("  TEST EMAIL — Simulating token near-expiry")
print("=" * 65)

# Step 1: Save the real creation date
cur.execute("SELECT TOKEN_CREATED_AT FROM SCIM_TOKEN_TRACKER WHERE INTEGRATION_NAME = 'AAD_SCIM_INTEGRATION'")
real_date = cur.fetchone()
real_created = real_date['TOKEN_CREATED_AT']
print(f"\n   📅 Real token created at: {real_created}")

# Step 2: Set creation date to 171 days ago → 9 days remaining → triggers 10-day alert
print("   🔧 Temporarily setting token age to 171 days (9 days until expiry)...")
cur.execute("""
    UPDATE SCIM_TOKEN_TRACKER SET
        TOKEN_CREATED_AT = DATEADD(DAY, -171, CURRENT_TIMESTAMP()),
        TOKEN_EXPIRES_AT = DATEADD(DAY, 9, CURRENT_TIMESTAMP()),
        ALERT_10_SENT = FALSE,
        ALERT_5_SENT = FALSE,
        ALERT_3_SENT = FALSE,
        ALERT_1_SENT = FALSE,
        ALERT_0_SENT = FALSE
    WHERE INTEGRATION_NAME = 'AAD_SCIM_INTEGRATION'
""")
print("   ✅ Tracker updated")

# Step 3: Call the stored procedure
print("\n   🚀 Calling SP_CHECK_SCIM_TOKEN_EXPIRY()...")
cur.execute("CALL SP_CHECK_SCIM_TOKEN_EXPIRY()")
result = cur.fetchone()
print(f"\n   📋 Result: {list(result.values())[0]}")

# Step 4: Check alert history
print("\n   📧 Alert history:")
cur.execute("SELECT * FROM SCIM_TOKEN_ALERT_HISTORY ORDER BY ALERT_SENT_AT DESC LIMIT 3")
rows = cur.fetchall()
for row in rows:
    print(f"      {row.get('ALERT_TYPE', '')} | {row.get('USER_EMAIL', '')} | {row.get('STATUS', '')} | {row.get('ALERT_SENT_AT', '')}")

if not rows:
    print("      (no alerts logged yet)")

# Step 5: Restore real creation date
print(f"\n   🔄 Restoring real token creation date: {real_created}")
cur.execute(f"""
    UPDATE SCIM_TOKEN_TRACKER SET
        TOKEN_CREATED_AT = '{real_created}'::TIMESTAMP_NTZ,
        TOKEN_EXPIRES_AT = DATEADD(DAY, 180, '{real_created}'::TIMESTAMP_NTZ),
        ALERT_10_SENT = FALSE,
        ALERT_5_SENT = FALSE,
        ALERT_3_SENT = FALSE,
        ALERT_1_SENT = FALSE,
        ALERT_0_SENT = FALSE,
        STATUS = 'HEALTHY'
    WHERE INTEGRATION_NAME = 'AAD_SCIM_INTEGRATION'
""")
print("   ✅ Tracker restored to original state")

print("\n" + "=" * 65)

cur.close()
conn.close()
print("🔒 Connection closed.")
