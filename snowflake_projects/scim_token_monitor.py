"""
SCIM Token Expiry Monitor — Background Daemon
================================================
Tracks the Snowflake SCIM token expiry date and sends an email
notification 10 days before the token expires.

How it works:
    1. On first run (or after a token refresh), it queries Snowflake
       to get the token creation date and calculates the 6-month expiry.
    2. Runs as a background daemon, checking once per day.
    3. Sends email alerts at 10 days, 5 days, 3 days, 1 day, and on
       the expiry day itself.
    4. Persists state to a local JSON file so it survives restarts.

Prerequisites:
    • Fill in the EMAIL_* and SNOWFLAKE_* settings in .env
    • For Gmail: enable 2FA and create an App Password
      (https://myaccount.google.com/apppasswords)

Usage:
    python scim_token_monitor.py                  # Run as daemon
    python scim_token_monitor.py --check-now      # One-time check
    python scim_token_monitor.py --status         # Show token status
    python scim_token_monitor.py --reset           # Reset tracked state
    python scim_token_monitor.py --send-test-email # Send a test email
"""

import os
import sys
import json
import time
import smtplib
import logging
import argparse
import schedule
from pathlib import Path
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import snowflake.connector
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()


# ─── Configuration ─────────────────────────────────────────────────────────────

# Snowflake
SNOWFLAKE_CONFIG = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
    "user":      os.getenv("SNOWFLAKE_USER"),
    "password":  os.getenv("SNOWFLAKE_PASSWORD"),
    "role":      os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
}

SCIM_INTEGRATION_NAME = os.getenv("SCIM_INTEGRATION_NAME", "AAD_SCIM_INTEGRATION")

# Email (SMTP)
EMAIL_SMTP_HOST     = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT     = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SENDER        = os.getenv("EMAIL_SENDER", "your_email@gmail.com")
EMAIL_PASSWORD      = os.getenv("EMAIL_PASSWORD", "your_app_password")
EMAIL_RECIPIENTS    = os.getenv("EMAIL_RECIPIENTS", "admin@example.com").split(",")

# Token lifespan (Snowflake SCIM tokens expire after 6 months)
TOKEN_LIFESPAN_DAYS = int(os.getenv("TOKEN_LIFESPAN_DAYS", "180"))

# Alert thresholds (days before expiry)
ALERT_THRESHOLDS = [10, 5, 3, 1, 0]

# State file — persists token creation date and alert history
STATE_FILE = Path(__file__).parent / ".scim_token_state.json"

# Daemon check interval (in hours)
CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "24"))


# ─── Logging ───────────────────────────────────────────────────────────────────

LOG_FILE = Path(__file__).parent / "scim_monitor.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("scim_monitor")


# ─── State Management ─────────────────────────────────────────────────────────

def load_state():
    """Load persisted state from the JSON file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    """Persist state to the JSON file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def reset_state():
    """Delete the state file to start fresh."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        logger.info("🗑️  State file deleted.")
    else:
        logger.info("ℹ️  No state file found — nothing to reset.")


# ─── Snowflake Helpers ────────────────────────────────────────────────────────

def get_snowflake_connection():
    """Create a Snowflake connection."""
    config = {k: v for k, v in SNOWFLAKE_CONFIG.items() if v and v != f"your_{k}"}

    if not all(k in config for k in ("account", "user", "password")):
        logger.error("❌ Missing Snowflake credentials in .env")
        sys.exit(1)

    try:
        conn = snowflake.connector.connect(**config)
        logger.info("✅ Connected to Snowflake")
        return conn
    except snowflake.connector.errors.DatabaseError as e:
        logger.error(f"❌ Snowflake connection failed: {e}")
        sys.exit(1)


def get_token_creation_date(conn):
    """
    Query the SCIM integration to determine when the token was created.
    Uses DESCRIBE SECURITY INTEGRATION and SHOW SECURITY INTEGRATIONS
    to find the creation/modification timestamp.
    """
    try:
        cursor = conn.cursor(snowflake.connector.DictCursor)

        # SHOW SECURITY INTEGRATIONS gives us the created_on timestamp
        cursor.execute("SHOW SECURITY INTEGRATIONS")
        integrations = cursor.fetchall()

        for row in integrations:
            name = row.get("name", row.get("NAME", ""))
            if name == SCIM_INTEGRATION_NAME:
                created_on = row.get("created_on", row.get("CREATED_ON", ""))
                if created_on:
                    if isinstance(created_on, datetime):
                        return created_on
                    return datetime.fromisoformat(str(created_on).replace("Z", "+00:00"))

        logger.warning(f"⚠️  Integration '{SCIM_INTEGRATION_NAME}' not found")
        return None

    except Exception as e:
        logger.error(f"❌ Error querying integration: {e}")
        return None
    finally:
        cursor.close()


# ─── Email Sending ─────────────────────────────────────────────────────────────

def send_email(subject, body_html):
    """Send an HTML email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = ", ".join(EMAIL_RECIPIENTS)

    # Plain-text fallback
    body_text = body_html.replace("<br>", "\n").replace("</p>", "\n")
    import re
    body_text = re.sub(r"<[^>]+>", "", body_text)

    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENTS, msg.as_string())

        logger.info(f"📧 Email sent: {subject}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ SMTP auth failed. Check EMAIL_SENDER and EMAIL_PASSWORD in .env")
        logger.error("   For Gmail: enable 2FA → create App Password → use that as EMAIL_PASSWORD")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False


def build_alert_email(days_remaining, expiry_date, integration_name, account):
    """Build the HTML email body for the expiry alert."""

    if days_remaining <= 0:
        urgency = "🔴 EXPIRED"
        urgency_color = "#dc2626"
        headline = "Your SCIM token has EXPIRED!"
    elif days_remaining <= 3:
        urgency = "🟠 CRITICAL"
        urgency_color = "#ea580c"
        headline = f"Your SCIM token expires in {days_remaining} day{'s' if days_remaining != 1 else ''}!"
    else:
        urgency = "🟡 WARNING"
        urgency_color = "#ca8a04"
        headline = f"Your SCIM token expires in {days_remaining} days"

    html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto;
                border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">

        <!-- Header -->
        <div style="background: linear-gradient(135deg, #1e3a5f, #2563eb); padding: 24px 32px; color: white;">
            <h1 style="margin: 0; font-size: 20px;">❄️ Snowflake SCIM Token Alert</h1>
            <p style="margin: 6px 0 0; opacity: 0.85; font-size: 14px;">Automated monitoring notification</p>
        </div>

        <!-- Body -->
        <div style="padding: 28px 32px;">

            <!-- Urgency badge -->
            <div style="display: inline-block; background: {urgency_color}; color: white;
                        padding: 6px 16px; border-radius: 20px; font-size: 13px; font-weight: 600;
                        margin-bottom: 16px;">
                {urgency}
            </div>

            <h2 style="margin: 0 0 16px; color: #1f2937; font-size: 18px;">{headline}</h2>

            <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                <tr style="border-bottom: 1px solid #f3f4f6;">
                    <td style="padding: 10px 0; color: #6b7280; font-size: 14px;">Integration</td>
                    <td style="padding: 10px 0; font-weight: 600; font-size: 14px;">{integration_name}</td>
                </tr>
                <tr style="border-bottom: 1px solid #f3f4f6;">
                    <td style="padding: 10px 0; color: #6b7280; font-size: 14px;">Account</td>
                    <td style="padding: 10px 0; font-weight: 600; font-size: 14px;">{account}</td>
                </tr>
                <tr style="border-bottom: 1px solid #f3f4f6;">
                    <td style="padding: 10px 0; color: #6b7280; font-size: 14px;">Expiry Date</td>
                    <td style="padding: 10px 0; font-weight: 600; font-size: 14px; color: {urgency_color};">
                        {expiry_date.strftime('%B %d, %Y at %I:%M %p')}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; color: #6b7280; font-size: 14px;">Days Remaining</td>
                    <td style="padding: 10px 0; font-weight: 600; font-size: 14px; color: {urgency_color};">
                        {days_remaining if days_remaining > 0 else 'EXPIRED'}
                    </td>
                </tr>
            </table>

            <!-- Action -->
            <div style="background: #f0f9ff; border-left: 4px solid #2563eb;
                        padding: 16px 20px; border-radius: 0 8px 8px 0; margin: 20px 0;">
                <p style="margin: 0 0 8px; font-weight: 600; color: #1e40af; font-size: 14px;">
                    🔧 How to renew:
                </p>
                <ol style="margin: 0; padding-left: 20px; color: #374151; font-size: 13px; line-height: 1.8;">
                    <li>Run <code>python create_scim_integration.py</code> to regenerate the token</li>
                    <li>Copy the new token from the console output</li>
                    <li>Update Azure AD → Enterprise App → Provisioning → Secret Token</li>
                    <li>Test the connection in Azure AD</li>
                </ol>
            </div>
        </div>

        <!-- Footer -->
        <div style="background: #f9fafb; padding: 16px 32px; border-top: 1px solid #e5e7eb;
                    font-size: 12px; color: #9ca3af;">
            Sent by SCIM Token Monitor • {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
    </div>
    """

    subject = f"[{urgency.split(' ')[0]}] Snowflake SCIM Token — {headline}"
    return subject, html


# ─── Core Logic ────────────────────────────────────────────────────────────────

def check_token_expiry():
    """Main check: compute days remaining and send alerts as needed."""
    logger.info("🔄 Running SCIM token expiry check...")

    state = load_state()

    # ── Determine token creation date ──────────────────────────────────────
    token_created_str = state.get("token_created")

    if token_created_str:
        token_created = datetime.fromisoformat(token_created_str)
        logger.info(f"   Token creation date (from state): {token_created.strftime('%Y-%m-%d %H:%M')}")
    else:
        # Query Snowflake to find the integration creation date
        logger.info("   No saved state — querying Snowflake for integration details...")
        conn = get_snowflake_connection()
        try:
            token_created = get_token_creation_date(conn)
        finally:
            conn.close()

        if not token_created:
            logger.error("❌ Could not determine token creation date. Aborting.")
            return

        # Make naive if timezone-aware for consistent comparison
        if token_created.tzinfo is not None:
            token_created = token_created.replace(tzinfo=None)

        # Persist
        state["token_created"] = token_created.isoformat()
        save_state(state)
        logger.info(f"   Token creation date (from Snowflake): {token_created.strftime('%Y-%m-%d %H:%M')}")

    # ── Calculate expiry ───────────────────────────────────────────────────
    expiry_date = token_created + timedelta(days=TOKEN_LIFESPAN_DAYS)
    now = datetime.now()
    days_remaining = (expiry_date - now).days

    logger.info(f"   📅 Token created:  {token_created.strftime('%Y-%m-%d')}")
    logger.info(f"   📅 Token expires:  {expiry_date.strftime('%Y-%m-%d')}")
    logger.info(f"   ⏳ Days remaining: {days_remaining}")

    # ── Determine if we should alert ───────────────────────────────────────
    alerts_sent = state.get("alerts_sent", [])

    for threshold in ALERT_THRESHOLDS:
        if days_remaining <= threshold and threshold not in alerts_sent:
            account = os.getenv("SNOWFLAKE_ACCOUNT", "unknown_account")
            subject, body = build_alert_email(
                days_remaining, expiry_date, SCIM_INTEGRATION_NAME, account
            )

            success = send_email(subject, body)
            if success:
                alerts_sent.append(threshold)
                state["alerts_sent"] = alerts_sent
                state["last_alert_date"] = now.isoformat()
                save_state(state)
                logger.info(f"   🔔 Alert sent for {threshold}-day threshold")
            break  # Send one alert per check cycle

    if days_remaining > max(ALERT_THRESHOLDS):
        logger.info(f"   ✅ Token is healthy — next alert at {max(ALERT_THRESHOLDS)} days before expiry")


def show_status():
    """Display current token status without sending any alerts."""
    state = load_state()

    print("\n" + "=" * 65)
    print("  SCIM TOKEN MONITOR — STATUS")
    print("=" * 65)

    if not state.get("token_created"):
        print("\n  ⚠️  No token state found. Run --check-now first to initialize.\n")
        return

    token_created = datetime.fromisoformat(state["token_created"])
    expiry_date = token_created + timedelta(days=TOKEN_LIFESPAN_DAYS)
    days_remaining = (expiry_date - datetime.now()).days

    print(f"\n  Integration:     {SCIM_INTEGRATION_NAME}")
    print(f"  Token created:   {token_created.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Token expires:   {expiry_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Days remaining:  {days_remaining}")
    print(f"  Alerts sent:     {state.get('alerts_sent', [])}")
    print(f"  Last alert:      {state.get('last_alert_date', 'Never')}")
    print(f"  State file:      {STATE_FILE}")
    print(f"  Log file:        {LOG_FILE}")

    if days_remaining <= 0:
        print("\n  🔴 TOKEN HAS EXPIRED — regenerate immediately!")
    elif days_remaining <= 10:
        print(f"\n  🟡 TOKEN EXPIRING SOON — {days_remaining} days left")
    else:
        print(f"\n  🟢 TOKEN IS HEALTHY")

    print("=" * 65 + "\n")


def send_test_email():
    """Send a test email to verify SMTP configuration."""
    logger.info("📧 Sending test email...")

    subject = "✅ SCIM Token Monitor — Test Email"
    body = """
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 500px; margin: 0 auto;
                border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #059669, #10b981); padding: 24px 32px; color: white;">
            <h1 style="margin: 0; font-size: 20px;">✅ Test Email Successful</h1>
        </div>
        <div style="padding: 24px 32px;">
            <p style="color: #374151;">Your SCIM Token Monitor email configuration is working correctly.</p>
            <p style="color: #6b7280; font-size: 13px;">
                You will receive alerts at <strong>10, 5, 3, 1, and 0 days</strong> before token expiry.
            </p>
        </div>
    </div>
    """

    success = send_email(subject, body)
    if success:
        logger.info("✅ Test email sent successfully!")
    else:
        logger.error("❌ Test email failed — check your EMAIL_* settings in .env")


# ─── Daemon ────────────────────────────────────────────────────────────────────

def run_daemon():
    """Run the monitor as a background daemon that checks once per day."""
    logger.info("=" * 65)
    logger.info("  SCIM TOKEN MONITOR — DAEMON STARTED")
    logger.info("=" * 65)
    logger.info(f"  Integration:    {SCIM_INTEGRATION_NAME}")
    logger.info(f"  Check interval: every {CHECK_INTERVAL_HOURS} hours")
    logger.info(f"  Alert days:     {ALERT_THRESHOLDS}")
    logger.info(f"  Recipients:     {', '.join(EMAIL_RECIPIENTS)}")
    logger.info(f"  State file:     {STATE_FILE}")
    logger.info(f"  Log file:       {LOG_FILE}")
    logger.info("=" * 65)

    # Run an immediate check on startup
    check_token_expiry()

    # Schedule recurring checks
    schedule.every(CHECK_INTERVAL_HOURS).hours.do(check_token_expiry)

    logger.info(f"\n⏰ Daemon running — next check in {CHECK_INTERVAL_HOURS} hours. Press Ctrl+C to stop.\n")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check the schedule every minute
    except KeyboardInterrupt:
        logger.info("\n🛑 Daemon stopped by user.")


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Monitor Snowflake SCIM token expiry and send email alerts"
    )
    parser.add_argument(
        "--check-now",
        action="store_true",
        help="Run a one-time expiry check (no daemon)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current token status",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset tracked state (alerts sent, creation date)",
    )
    parser.add_argument(
        "--send-test-email",
        action="store_true",
        help="Send a test email to verify SMTP configuration",
    )
    args = parser.parse_args()

    if args.reset:
        reset_state()
    elif args.status:
        show_status()
    elif args.send_test_email:
        send_test_email()
    elif args.check_now:
        check_token_expiry()
    else:
        run_daemon()


if __name__ == "__main__":
    main()
