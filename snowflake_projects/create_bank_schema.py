"""
Bank Database Schema Generator
================================
Creates a realistic BANK schema in Snowflake's TEST_BANK database
and populates all tables with 1000 rows of fake data using Faker.

Tables:
  - BRANCHES       : Bank branch locations
  - CUSTOMERS      : Customer profiles
  - ACCOUNTS       : Bank accounts (Savings, Checking, etc.)
  - TRANSACTIONS   : Account transaction history
  - EMPLOYEES      : Bank staff
  - LOANS          : Customer loans
  - LOAN_PAYMENTS  : Loan repayment records
  - CARDS          : Debit & Credit cards

Usage:
    python create_bank_schema.py
"""

import os
import sys
import random
from datetime import datetime, timedelta
from decimal import Decimal

import snowflake.connector
from dotenv import load_dotenv
from faker import Faker

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
fake = Faker()
Faker.seed(42)
random.seed(42)

# ─── Configuration ─────────────────────────────────────────────────────────────
NUM_ROWS = 1000
NUM_BRANCHES = 50
NUM_EMPLOYEES = 200

ACCOUNT_TYPES = ['Savings', 'Checking', 'Fixed Deposit', 'Recurring Deposit', 'Current']
ACCOUNT_STATUSES = ['Active', 'Inactive', 'Closed', 'Frozen']
TRANSACTION_TYPES = ['Deposit', 'Withdrawal', 'Transfer', 'Payment', 'Refund', 'Fee', 'Interest']
TRANSACTION_CHANNELS = ['Branch', 'ATM', 'Online', 'Mobile App', 'UPI', 'NEFT', 'RTGS', 'IMPS']
LOAN_TYPES = ['Home Loan', 'Personal Loan', 'Auto Loan', 'Education Loan', 'Business Loan', 'Gold Loan']
LOAN_STATUSES = ['Active', 'Closed', 'Defaulted', 'Restructured']
CARD_TYPES = ['Debit', 'Credit']
CARD_NETWORKS = ['Visa', 'Mastercard', 'RuPay', 'American Express']
CARD_STATUSES = ['Active', 'Blocked', 'Expired', 'Cancelled']
EMPLOYEE_DEPTS = ['Retail Banking', 'Operations', 'Loans', 'Customer Service', 'IT', 'Risk Management', 'Compliance', 'Treasury']
EMPLOYEE_POSITIONS = ['Branch Manager', 'Assistant Manager', 'Relationship Manager', 'Teller', 'Loan Officer', 'Analyst', 'Clerk', 'VP']


# ─── DDL Statements ───────────────────────────────────────────────────────────

DDL_STATEMENTS = [
    # Schema
    "CREATE SCHEMA IF NOT EXISTS BANK",
    "USE SCHEMA BANK",

    # BRANCHES
    """
    CREATE OR REPLACE TABLE BANK.BRANCHES (
        BRANCH_ID       INT PRIMARY KEY,
        BRANCH_NAME     VARCHAR(100) NOT NULL,
        BRANCH_CODE     VARCHAR(20) NOT NULL UNIQUE,
        ADDRESS         VARCHAR(255),
        CITY            VARCHAR(100),
        STATE           VARCHAR(100),
        ZIP_CODE        VARCHAR(20),
        PHONE           VARCHAR(20),
        MANAGER_NAME    VARCHAR(100),
        OPENED_DATE     DATE,
        IS_ACTIVE       BOOLEAN DEFAULT TRUE
    )
    """,

    # CUSTOMERS
    """
    CREATE OR REPLACE TABLE BANK.CUSTOMERS (
        CUSTOMER_ID     INT PRIMARY KEY,
        FIRST_NAME      VARCHAR(100) NOT NULL,
        LAST_NAME       VARCHAR(100) NOT NULL,
        EMAIL           VARCHAR(200) UNIQUE,
        PHONE           VARCHAR(20),
        DATE_OF_BIRTH   DATE,
        GENDER          VARCHAR(10),
        ADDRESS         VARCHAR(255),
        CITY            VARCHAR(100),
        STATE           VARCHAR(100),
        ZIP_CODE        VARCHAR(20),
        COUNTRY         VARCHAR(50) DEFAULT 'India',
        PAN_NUMBER      VARCHAR(20),
        AADHAR_NUMBER   VARCHAR(20),
        OCCUPATION      VARCHAR(100),
        ANNUAL_INCOME   DECIMAL(15,2),
        CUSTOMER_SINCE  DATE,
        KYC_STATUS      VARCHAR(20) DEFAULT 'Verified',
        BRANCH_ID       INT REFERENCES BANK.BRANCHES(BRANCH_ID)
    )
    """,

    # EMPLOYEES
    """
    CREATE OR REPLACE TABLE BANK.EMPLOYEES (
        EMPLOYEE_ID     INT PRIMARY KEY,
        FIRST_NAME      VARCHAR(100) NOT NULL,
        LAST_NAME       VARCHAR(100) NOT NULL,
        EMAIL           VARCHAR(200) UNIQUE,
        PHONE           VARCHAR(20),
        DEPARTMENT      VARCHAR(100),
        POSITION        VARCHAR(100),
        HIRE_DATE       DATE,
        SALARY          DECIMAL(12,2),
        BRANCH_ID       INT REFERENCES BANK.BRANCHES(BRANCH_ID),
        MANAGER_ID      INT,
        IS_ACTIVE       BOOLEAN DEFAULT TRUE
    )
    """,

    # ACCOUNTS
    """
    CREATE OR REPLACE TABLE BANK.ACCOUNTS (
        ACCOUNT_ID      INT PRIMARY KEY,
        ACCOUNT_NUMBER  VARCHAR(20) NOT NULL UNIQUE,
        CUSTOMER_ID     INT NOT NULL REFERENCES BANK.CUSTOMERS(CUSTOMER_ID),
        ACCOUNT_TYPE    VARCHAR(50) NOT NULL,
        BALANCE         DECIMAL(15,2) DEFAULT 0.00,
        CURRENCY        VARCHAR(10) DEFAULT 'INR',
        INTEREST_RATE   DECIMAL(5,2),
        OPENED_DATE     DATE NOT NULL,
        CLOSED_DATE     DATE,
        STATUS          VARCHAR(20) DEFAULT 'Active',
        BRANCH_ID       INT REFERENCES BANK.BRANCHES(BRANCH_ID)
    )
    """,

    # TRANSACTIONS
    """
    CREATE OR REPLACE TABLE BANK.TRANSACTIONS (
        TRANSACTION_ID      INT PRIMARY KEY,
        ACCOUNT_ID          INT NOT NULL REFERENCES BANK.ACCOUNTS(ACCOUNT_ID),
        TRANSACTION_TYPE    VARCHAR(50) NOT NULL,
        AMOUNT              DECIMAL(15,2) NOT NULL,
        BALANCE_AFTER       DECIMAL(15,2),
        TRANSACTION_DATE    TIMESTAMP NOT NULL,
        DESCRIPTION         VARCHAR(255),
        CHANNEL             VARCHAR(50),
        REFERENCE_NUMBER    VARCHAR(50),
        STATUS              VARCHAR(20) DEFAULT 'Completed',
        COUNTERPARTY_ACCOUNT VARCHAR(20)
    )
    """,

    # LOANS
    """
    CREATE OR REPLACE TABLE BANK.LOANS (
        LOAN_ID             INT PRIMARY KEY,
        CUSTOMER_ID         INT NOT NULL REFERENCES BANK.CUSTOMERS(CUSTOMER_ID),
        LOAN_TYPE           VARCHAR(50) NOT NULL,
        PRINCIPAL_AMOUNT    DECIMAL(15,2) NOT NULL,
        INTEREST_RATE       DECIMAL(5,2) NOT NULL,
        TENURE_MONTHS       INT NOT NULL,
        EMI_AMOUNT          DECIMAL(12,2),
        DISBURSEMENT_DATE   DATE,
        MATURITY_DATE       DATE,
        OUTSTANDING_BALANCE DECIMAL(15,2),
        STATUS              VARCHAR(20) DEFAULT 'Active',
        COLLATERAL_TYPE     VARCHAR(100),
        COLLATERAL_VALUE    DECIMAL(15,2),
        BRANCH_ID           INT REFERENCES BANK.BRANCHES(BRANCH_ID),
        APPROVED_BY         INT REFERENCES BANK.EMPLOYEES(EMPLOYEE_ID)
    )
    """,

    # LOAN_PAYMENTS
    """
    CREATE OR REPLACE TABLE BANK.LOAN_PAYMENTS (
        PAYMENT_ID      INT PRIMARY KEY,
        LOAN_ID         INT NOT NULL REFERENCES BANK.LOANS(LOAN_ID),
        PAYMENT_DATE    DATE NOT NULL,
        AMOUNT_PAID     DECIMAL(12,2) NOT NULL,
        PRINCIPAL_PART  DECIMAL(12,2),
        INTEREST_PART   DECIMAL(12,2),
        PENALTY         DECIMAL(10,2) DEFAULT 0,
        PAYMENT_MODE    VARCHAR(50),
        STATUS          VARCHAR(20) DEFAULT 'Completed'
    )
    """,

    # CARDS
    """
    CREATE OR REPLACE TABLE BANK.CARDS (
        CARD_ID         INT PRIMARY KEY,
        CARD_NUMBER     VARCHAR(20) NOT NULL,
        CUSTOMER_ID     INT NOT NULL REFERENCES BANK.CUSTOMERS(CUSTOMER_ID),
        ACCOUNT_ID      INT REFERENCES BANK.ACCOUNTS(ACCOUNT_ID),
        CARD_TYPE       VARCHAR(20) NOT NULL,
        CARD_NETWORK    VARCHAR(30),
        EXPIRY_DATE     DATE NOT NULL,
        CVV             VARCHAR(5),
        CREDIT_LIMIT    DECIMAL(12,2),
        ISSUED_DATE     DATE,
        STATUS          VARCHAR(20) DEFAULT 'Active',
        PIN_SET         BOOLEAN DEFAULT FALSE
    )
    """
]


# ─── Data Generators ──────────────────────────────────────────────────────────

def generate_pan():
    """Generate a realistic Indian PAN number."""
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return (
        random.choice(letters) + random.choice(letters) + random.choice(letters)
        + 'P' + random.choice(letters)
        + str(random.randint(1000, 9999))
        + random.choice(letters)
    )


def generate_aadhar():
    """Generate a 12-digit Aadhar-like number."""
    return ''.join([str(random.randint(0, 9)) for _ in range(12)])


def generate_branches():
    """Generate branch data."""
    print("  🏦 Generating BRANCHES...")
    rows = []
    cities = ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Hyderabad', 'Pune',
              'Kolkata', 'Ahmedabad', 'Jaipur', 'Lucknow', 'Kochi', 'Indore',
              'Chandigarh', 'Coimbatore', 'Nagpur', 'Bhopal', 'Visakhapatnam',
              'Vadodara', 'Surat', 'Thiruvananthapuram']
    states = {
        'Mumbai': 'Maharashtra', 'Delhi': 'Delhi', 'Bangalore': 'Karnataka',
        'Chennai': 'Tamil Nadu', 'Hyderabad': 'Telangana', 'Pune': 'Maharashtra',
        'Kolkata': 'West Bengal', 'Ahmedabad': 'Gujarat', 'Jaipur': 'Rajasthan',
        'Lucknow': 'Uttar Pradesh', 'Kochi': 'Kerala', 'Indore': 'Madhya Pradesh',
        'Chandigarh': 'Chandigarh', 'Coimbatore': 'Tamil Nadu', 'Nagpur': 'Maharashtra',
        'Bhopal': 'Madhya Pradesh', 'Visakhapatnam': 'Andhra Pradesh',
        'Vadodara': 'Gujarat', 'Surat': 'Gujarat', 'Thiruvananthapuram': 'Kerala'
    }
    for i in range(1, NUM_BRANCHES + 1):
        city = random.choice(cities)
        rows.append((
            i,
            f"{city} {fake.street_suffix()} Branch",
            f"BR{str(i).zfill(4)}",
            fake.street_address(),
            city,
            states[city],
            fake.zipcode(),
            fake.phone_number()[:15],
            fake.name(),
            fake.date_between(start_date='-20y', end_date='-1y'),
            random.random() > 0.05
        ))
    return rows


def generate_customers():
    """Generate customer data."""
    print("  👤 Generating CUSTOMERS...")
    rows = []
    genders = ['Male', 'Female', 'Other']
    occupations = ['Engineer', 'Doctor', 'Teacher', 'Business Owner', 'Accountant',
                   'Lawyer', 'IT Professional', 'Government Employee', 'Retired',
                   'Student', 'Freelancer', 'Farmer', 'Artist', 'Banker']
    kyc_statuses = ['Verified', 'Pending', 'Rejected', 'Expired']

    for i in range(1, NUM_ROWS + 1):
        gender = random.choice(genders)
        first = fake.first_name_male() if gender == 'Male' else fake.first_name_female()
        last = fake.last_name()
        rows.append((
            i,
            first,
            last,
            f"{first.lower()}.{last.lower()}{random.randint(1,999)}@{fake.free_email_domain()}",
            fake.phone_number()[:15],
            fake.date_of_birth(minimum_age=18, maximum_age=80),
            gender,
            fake.street_address(),
            fake.city(),
            fake.state(),
            fake.zipcode(),
            'India',
            generate_pan(),
            generate_aadhar(),
            random.choice(occupations),
            round(random.uniform(200000, 5000000), 2),
            fake.date_between(start_date='-15y', end_date='-30d'),
            random.choices(kyc_statuses, weights=[85, 8, 2, 5])[0],
            random.randint(1, NUM_BRANCHES)
        ))
    return rows


def generate_employees():
    """Generate employee data."""
    print("  👨‍💼 Generating EMPLOYEES...")
    rows = []
    for i in range(1, NUM_EMPLOYEES + 1):
        dept = random.choice(EMPLOYEE_DEPTS)
        position = random.choice(EMPLOYEE_POSITIONS)
        base_salary = {
            'Branch Manager': 120000, 'VP': 200000, 'Assistant Manager': 80000,
            'Relationship Manager': 60000, 'Loan Officer': 55000, 'Analyst': 50000,
            'Teller': 30000, 'Clerk': 25000
        }
        salary = base_salary.get(position, 40000) * random.uniform(0.9, 1.4)
        rows.append((
            i,
            fake.first_name(),
            fake.last_name(),
            fake.company_email(),
            fake.phone_number()[:15],
            dept,
            position,
            fake.date_between(start_date='-15y', end_date='-30d'),
            round(salary, 2),
            random.randint(1, NUM_BRANCHES),
            random.choice([None, random.randint(1, max(1, i - 1))]) if i > 1 else None,
            random.random() > 0.05
        ))
    return rows


def generate_accounts(customers):
    """Generate account data — some customers have multiple accounts."""
    print("  🏧 Generating ACCOUNTS...")
    rows = []
    account_id = 1
    for cust_id in range(1, NUM_ROWS + 1):
        # Each customer gets 1–3 accounts
        num_accounts = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
        for _ in range(num_accounts):
            if account_id > NUM_ROWS:
                break
            acc_type = random.choice(ACCOUNT_TYPES)
            interest_rates = {
                'Savings': random.uniform(3, 7),
                'Checking': 0.0,
                'Fixed Deposit': random.uniform(6, 9),
                'Recurring Deposit': random.uniform(5.5, 8),
                'Current': 0.0
            }
            status = random.choices(ACCOUNT_STATUSES, weights=[80, 10, 7, 3])[0]
            opened = fake.date_between(start_date='-10y', end_date='-30d')
            closed = fake.date_between(start_date=opened, end_date='today') if status == 'Closed' else None

            rows.append((
                account_id,
                f"10{random.randint(10, 99)}{str(account_id).zfill(10)}",
                cust_id,
                acc_type,
                round(random.uniform(500, 2500000), 2),
                'INR',
                round(interest_rates[acc_type], 2),
                opened,
                closed,
                status,
                random.randint(1, NUM_BRANCHES)
            ))
            account_id += 1
    return rows[:NUM_ROWS]


def generate_transactions(accounts):
    """Generate transaction data."""
    print("  💳 Generating TRANSACTIONS...")
    rows = []
    account_ids = [a[0] for a in accounts]
    account_balances = {a[0]: a[4] for a in accounts}

    for i in range(1, NUM_ROWS + 1):
        acc_id = random.choice(account_ids)
        txn_type = random.choice(TRANSACTION_TYPES)
        amount = round(random.uniform(100, 200000), 2)
        balance = account_balances.get(acc_id, 50000)

        if txn_type in ('Withdrawal', 'Payment', 'Fee'):
            balance_after = round(balance - amount, 2)
        else:
            balance_after = round(balance + amount, 2)

        descriptions = {
            'Deposit': f'Cash deposit at branch',
            'Withdrawal': f'ATM withdrawal',
            'Transfer': f'Fund transfer to {fake.name()}',
            'Payment': f'Bill payment - {random.choice(["Electricity", "Water", "Internet", "Phone", "Insurance"])}',
            'Refund': f'Refund from {fake.company()}',
            'Fee': f'Service charge',
            'Interest': f'Quarterly interest credit'
        }

        rows.append((
            i,
            acc_id,
            txn_type,
            amount,
            balance_after,
            fake.date_time_between(start_date='-2y', end_date='now'),
            descriptions[txn_type],
            random.choice(TRANSACTION_CHANNELS),
            f"TXN{fake.bothify('##??####??##').upper()}",
            random.choices(['Completed', 'Pending', 'Failed', 'Reversed'], weights=[90, 5, 3, 2])[0],
            f"10{random.randint(10, 99)}{str(random.randint(1, NUM_ROWS)).zfill(10)}" if txn_type == 'Transfer' else None
        ))
    return rows


def generate_loans(customers, employees):
    """Generate loan data."""
    print("  📋 Generating LOANS...")
    rows = []
    collateral_types = ['Property', 'Vehicle', 'Gold', 'Fixed Deposit', 'Securities', None]
    num_loans = min(NUM_ROWS, 500)  # Not all customers have loans

    for i in range(1, num_loans + 1):
        loan_type = random.choice(LOAN_TYPES)
        principal_ranges = {
            'Home Loan': (1000000, 10000000),
            'Personal Loan': (50000, 2000000),
            'Auto Loan': (200000, 5000000),
            'Education Loan': (100000, 3000000),
            'Business Loan': (500000, 8000000),
            'Gold Loan': (50000, 1500000)
        }
        lo, hi = principal_ranges[loan_type]
        principal = round(random.uniform(lo, hi), 2)
        rate = round(random.uniform(7, 18), 2)
        tenure = random.choice([12, 24, 36, 48, 60, 84, 120, 180, 240, 360])

        # Simple EMI calculation: EMI = P * r * (1+r)^n / ((1+r)^n - 1)
        monthly_rate = rate / 12 / 100
        if monthly_rate > 0:
            emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure) / (((1 + monthly_rate) ** tenure) - 1)
        else:
            emi = principal / tenure

        disbursement = fake.date_between(start_date='-8y', end_date='-30d')
        maturity = disbursement + timedelta(days=tenure * 30)
        status = random.choices(LOAN_STATUSES, weights=[60, 25, 10, 5])[0]
        outstanding = round(principal * random.uniform(0.1, 0.95), 2) if status == 'Active' else 0

        collateral = random.choice(collateral_types)
        collateral_value = round(principal * random.uniform(1.1, 2.0), 2) if collateral else None

        rows.append((
            i,
            random.randint(1, NUM_ROWS),
            loan_type,
            principal,
            rate,
            tenure,
            round(emi, 2),
            disbursement,
            maturity,
            outstanding,
            status,
            collateral,
            collateral_value,
            random.randint(1, NUM_BRANCHES),
            random.randint(1, NUM_EMPLOYEES)
        ))
    return rows


def generate_loan_payments(loans):
    """Generate loan payment records."""
    print("  💰 Generating LOAN_PAYMENTS...")
    rows = []
    payment_modes = ['Auto Debit', 'NEFT', 'UPI', 'Cash', 'Cheque', 'Online']
    payment_id = 1

    for loan in loans:
        if payment_id > NUM_ROWS:
            break
        loan_id = loan[0]
        emi = loan[6]
        disbursement = loan[7]

        # Generate 1–4 payment records per loan
        num_payments = random.randint(1, 4)
        for j in range(num_payments):
            if payment_id > NUM_ROWS:
                break
            payment_date = disbursement + timedelta(days=30 * (j + 1))
            if payment_date > datetime.now().date():
                break

            interest_part = round(emi * random.uniform(0.3, 0.7), 2)
            principal_part = round(emi - interest_part, 2)
            penalty = round(random.uniform(0, 500), 2) if random.random() < 0.08 else 0

            rows.append((
                payment_id,
                loan_id,
                payment_date,
                round(emi + penalty, 2),
                principal_part,
                interest_part,
                penalty,
                random.choice(payment_modes),
                random.choices(['Completed', 'Bounced', 'Pending'], weights=[90, 7, 3])[0]
            ))
            payment_id += 1

    return rows[:NUM_ROWS]


def generate_cards(customers, accounts):
    """Generate card data."""
    print("  💳 Generating CARDS...")
    rows = []
    account_ids = [a[0] for a in accounts]

    for i in range(1, NUM_ROWS + 1):
        card_type = random.choice(CARD_TYPES)
        network = random.choice(CARD_NETWORKS)
        issued = fake.date_between(start_date='-5y', end_date='-30d')
        expiry = issued + timedelta(days=random.choice([365 * 3, 365 * 5]))
        status = 'Expired' if expiry < datetime.now().date() else random.choices(
            ['Active', 'Blocked', 'Cancelled'], weights=[85, 10, 5])[0]

        credit_limit = round(random.uniform(25000, 1000000), 2) if card_type == 'Credit' else None

        rows.append((
            i,
            fake.credit_card_number(card_type='visa16'),
            random.randint(1, NUM_ROWS),
            random.choice(account_ids),
            card_type,
            network,
            expiry,
            str(random.randint(100, 999)),
            credit_limit,
            issued,
            status,
            random.random() > 0.1
        ))
    return rows


# ─── Batch Insert ──────────────────────────────────────────────────────────────

def batch_insert(conn, table_name, columns, data, batch_size=500):
    """Insert data in batches using parameterized queries."""
    cursor = conn.cursor()
    placeholders = ', '.join(['%s'] * len(columns))
    col_names = ', '.join(columns)
    query = f"INSERT INTO BANK.{table_name} ({col_names}) VALUES ({placeholders})"

    total = len(data)
    for start in range(0, total, batch_size):
        batch = data[start:start + batch_size]
        cursor.executemany(query, batch)

    print(f"     ✅ Inserted {total} rows into BANK.{table_name}")
    cursor.close()


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    config = {
        "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
        "user":      os.getenv("SNOWFLAKE_USER"),
        "password":  os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database":  "TEST_BANK",
        "role":      os.getenv("SNOWFLAKE_ROLE"),
    }
    config = {k: v for k, v in config.items() if v}

    print("🔗 Connecting to Snowflake...")
    conn = snowflake.connector.connect(**config)
    print("✅ Connected!\n")

    try:
        cursor = conn.cursor()

        # ── Step 1: Create schema & tables ─────────────────────────────────
        print("📐 Creating BANK schema and tables...")
        for ddl in DDL_STATEMENTS:
            cursor.execute(ddl)
        print("✅ Schema and all 8 tables created!\n")

        # ── Step 2: Generate fake data ─────────────────────────────────────
        print("🔄 Generating fake data with Faker...")
        branches    = generate_branches()
        customers   = generate_customers()
        employees   = generate_employees()
        accounts    = generate_accounts(customers)
        transactions = generate_transactions(accounts)
        loans       = generate_loans(customers, employees)
        loan_payments = generate_loan_payments(loans)
        cards       = generate_cards(customers, accounts)
        print()

        # ── Step 3: Insert data ────────────────────────────────────────────
        print("📤 Inserting data into Snowflake...\n")

        batch_insert(conn, 'BRANCHES', [
            'BRANCH_ID', 'BRANCH_NAME', 'BRANCH_CODE', 'ADDRESS', 'CITY',
            'STATE', 'ZIP_CODE', 'PHONE', 'MANAGER_NAME', 'OPENED_DATE', 'IS_ACTIVE'
        ], branches)

        batch_insert(conn, 'CUSTOMERS', [
            'CUSTOMER_ID', 'FIRST_NAME', 'LAST_NAME', 'EMAIL', 'PHONE',
            'DATE_OF_BIRTH', 'GENDER', 'ADDRESS', 'CITY', 'STATE', 'ZIP_CODE',
            'COUNTRY', 'PAN_NUMBER', 'AADHAR_NUMBER', 'OCCUPATION', 'ANNUAL_INCOME',
            'CUSTOMER_SINCE', 'KYC_STATUS', 'BRANCH_ID'
        ], customers)

        batch_insert(conn, 'EMPLOYEES', [
            'EMPLOYEE_ID', 'FIRST_NAME', 'LAST_NAME', 'EMAIL', 'PHONE',
            'DEPARTMENT', 'POSITION', 'HIRE_DATE', 'SALARY', 'BRANCH_ID',
            'MANAGER_ID', 'IS_ACTIVE'
        ], employees)

        batch_insert(conn, 'ACCOUNTS', [
            'ACCOUNT_ID', 'ACCOUNT_NUMBER', 'CUSTOMER_ID', 'ACCOUNT_TYPE',
            'BALANCE', 'CURRENCY', 'INTEREST_RATE', 'OPENED_DATE', 'CLOSED_DATE',
            'STATUS', 'BRANCH_ID'
        ], accounts)

        batch_insert(conn, 'TRANSACTIONS', [
            'TRANSACTION_ID', 'ACCOUNT_ID', 'TRANSACTION_TYPE', 'AMOUNT',
            'BALANCE_AFTER', 'TRANSACTION_DATE', 'DESCRIPTION', 'CHANNEL',
            'REFERENCE_NUMBER', 'STATUS', 'COUNTERPARTY_ACCOUNT'
        ], transactions)

        batch_insert(conn, 'LOANS', [
            'LOAN_ID', 'CUSTOMER_ID', 'LOAN_TYPE', 'PRINCIPAL_AMOUNT',
            'INTEREST_RATE', 'TENURE_MONTHS', 'EMI_AMOUNT', 'DISBURSEMENT_DATE',
            'MATURITY_DATE', 'OUTSTANDING_BALANCE', 'STATUS', 'COLLATERAL_TYPE',
            'COLLATERAL_VALUE', 'BRANCH_ID', 'APPROVED_BY'
        ], loans)

        batch_insert(conn, 'LOAN_PAYMENTS', [
            'PAYMENT_ID', 'LOAN_ID', 'PAYMENT_DATE', 'AMOUNT_PAID',
            'PRINCIPAL_PART', 'INTEREST_PART', 'PENALTY', 'PAYMENT_MODE', 'STATUS'
        ], loan_payments)

        batch_insert(conn, 'CARDS', [
            'CARD_ID', 'CARD_NUMBER', 'CUSTOMER_ID', 'ACCOUNT_ID', 'CARD_TYPE',
            'CARD_NETWORK', 'EXPIRY_DATE', 'CVV', 'CREDIT_LIMIT', 'ISSUED_DATE',
            'STATUS', 'PIN_SET'
        ], cards)

        # ── Step 4: Verify ─────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  📊 BANK SCHEMA — TABLE ROW COUNTS")
        print("=" * 60)
        tables = ['BRANCHES', 'CUSTOMERS', 'EMPLOYEES', 'ACCOUNTS',
                  'TRANSACTIONS', 'LOANS', 'LOAN_PAYMENTS', 'CARDS']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM BANK.{table}")
            count = cursor.fetchone()[0]
            print(f"  {table:20s} : {count:,} rows")
        print("=" * 60)
        print("\n🎉 Bank database setup complete!")

        cursor.close()

    finally:
        conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    main()
