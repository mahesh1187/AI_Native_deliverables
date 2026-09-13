"""Fix PUBLIC schema ownership back to ACCOUNTADMIN, then redeploy."""
import os
import sys
import snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    role="ACCOUNTADMIN",
)

cur = conn.cursor()

# Check current schema ownership
cur.execute("SHOW SCHEMAS LIKE 'PUBLIC' IN DATABASE TEST_BANK")
for row in cur.fetchall():
    print(f"Schema: {row[1]}, Owner: {row[5]}")

# Reclaim ownership of PUBLIC schema
try:
    cur.execute("GRANT OWNERSHIP ON SCHEMA TEST_BANK.PUBLIC TO ROLE ACCOUNTADMIN REVOKE CURRENT GRANTS")
    print("Ownership of PUBLIC schema reclaimed by ACCOUNTADMIN")
except Exception as e:
    print(f"Error: {str(e)[:200]}")

# Grant all privileges back
try:
    cur.execute("GRANT ALL PRIVILEGES ON SCHEMA TEST_BANK.PUBLIC TO ROLE ACCOUNTADMIN")
    print("All privileges granted on PUBLIC schema")
except Exception as e:
    print(f"Note: {str(e)[:200]}")

cur.close()
conn.close()
print("\nDone - now redeploy sp_scim_token_tracker.py")
