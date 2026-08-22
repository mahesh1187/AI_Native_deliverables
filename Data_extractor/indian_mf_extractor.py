"""
=============================================================================
 Indian Mutual Fund Data Extractor
=============================================================================
 Data Sources:
   1. mfapi.in      – NAV history, scheme metadata, fund search
   2. AMFI India    – Live NAV for all schemes (official regulator data)
   3. AMFI Portfolio – Monthly portfolio disclosures (equity holdings)

 Features:
   - Search mutual funds by name / AMC / category
   - Fetch live NAV (current day)
   - Fetch full historical NAV with analytics (CAGR, absolute returns)
   - Fetch all AMFI schemes with live NAV
   - Fetch monthly portfolio holdings (top stocks held by fund)
   - AMC & category summaries
   - Export everything to CSV / JSON
   - CLI quick-lookup mode: python indian_mf_extractor.py <scheme_code>

 Install dependencies:
   pip install requests pandas tabulate openpyxl

 Author : AI_Native_Deliverables
 Date   : 2026-08
=============================================================================
"""

import requests
import pandas as pd
import json
import os
import sys
import time
from datetime import datetime, date
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MFAPI_BASE         = "https://api.mfapi.in/mf"
AMFI_NAV_URL       = "https://www.amfiindia.com/spages/NAVAll.txt"
AMFI_PORTFOLIO_URL = "https://www.amfiindia.com/modules/PortfolioDetails"

REQUEST_TIMEOUT  = 30   # seconds
RETRY_ATTEMPTS   = 3
RETRY_DELAY      = 2    # seconds between retries

OUTPUT_DIR = "mf_output"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ---------------------------------------------------------------------------
# Pretty-print table (no tabulate dependency required – falls back gracefully)
# ---------------------------------------------------------------------------

try:
    from tabulate import tabulate as _tabulate
    def _print_table(df, max_rows=15):
        print(_tabulate(df.head(max_rows), headers="keys", tablefmt="rounded_outline", showindex=False))
except ImportError:
    def _print_table(df, max_rows=15):
        print(df.head(max_rows).to_string(index=False))


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _get(url: str, params: dict = None, data: dict = None, method: str = "GET"):
    """HTTP wrapper with retry logic. Returns JSON, raw text, or None."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            if method == "POST":
                resp = requests.post(url, data=data, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            else:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                return resp.text
        except requests.exceptions.RequestException as exc:
            print(f"  [Attempt {attempt}/{RETRY_ATTEMPTS}] Request failed: {exc}")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)
    return None


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_csv(df: pd.DataFrame, filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  Saved CSV  -> {path}")


def save_json(data, filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved JSON -> {path}")


# =============================================================================
# MODULE 1 – Fund Search & Listing  (mfapi.in)
# =============================================================================

def get_all_funds() -> pd.DataFrame:
    """
    Fetch the master list of all Indian mutual fund schemes from mfapi.in.
    Returns a DataFrame: schemeCode, schemeName
    """
    print("\n[1] Fetching master fund list from mfapi.in ...")
    data = _get(MFAPI_BASE)
    if not data:
        print("  Failed to fetch fund list.")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    print(f"  {len(df):,} schemes found.")
    return df


def search_funds(query: str, df_all: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Search mutual fund schemes by keyword (name match)."""
    if df_all is None or df_all.empty:
        df_all = get_all_funds()
    mask   = df_all["schemeName"].str.contains(query, case=False, na=False)
    result = df_all[mask].reset_index(drop=True)
    print(f"\n  Search '{query}' -> {len(result)} matches")
    return result


# =============================================================================
# MODULE 2 – Fund Details & NAV History  (mfapi.in)
# =============================================================================

def get_fund_details(scheme_code: int) -> dict:
    """
    Returns full details of a scheme:
      meta : fund_house, scheme_type, scheme_category, isin, etc.
      data : list of {date, nav} dicts (full NAV history)
    """
    print(f"\n[2] Fetching details for scheme code {scheme_code} ...")
    url  = f"{MFAPI_BASE}/{scheme_code}"
    resp = _get(url)
    if not resp or "meta" not in resp:
        print(f"  Could not fetch scheme {scheme_code}.")
        return {}
    meta = resp["meta"]
    print(f"  Scheme   : {meta.get('scheme_name')}")
    print(f"  AMC      : {meta.get('fund_house')}")
    print(f"  Type     : {meta.get('scheme_type')} | {meta.get('scheme_category')}")
    print(f"  ISIN     : {meta.get('isin_growth')}")
    print(f"  NAV records: {len(resp.get('data', [])):,}")
    return resp


def get_nav_history(scheme_code: int) -> pd.DataFrame:
    """
    Returns historical NAV data for a scheme as a DataFrame.
    Columns: date (datetime), nav (float)
    """
    details = get_fund_details(scheme_code)
    if not details:
        return pd.DataFrame()
    df = pd.DataFrame(details.get("data", []))
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    df["nav"]  = df["nav"].astype(float)
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def get_current_nav(scheme_code: int) -> Optional[float]:
    """Returns the latest (most recent) NAV for a scheme."""
    df = get_nav_history(scheme_code)
    if df.empty:
        return None
    return df.iloc[-1]["nav"]


# =============================================================================
# MODULE 3 – AMFI Live NAV (Official, All Funds)
# =============================================================================

def get_amfi_all_nav() -> pd.DataFrame:
    """
    Downloads the official AMFI NAV file (all schemes, all AMCs).
    Pipe-delimited format published daily by AMFI India.
    Returns a clean DataFrame with columns:
      scheme_code, isin_growth, isin_div_reinvest, scheme_name,
      plan, option, nav, date, amc, category
    """
    print("\n[3] Downloading AMFI NAV data (official regulator source) ...")
    raw = _get(AMFI_NAV_URL)
    if not raw:
        print("  Failed to fetch AMFI NAV data.")
        return pd.DataFrame()

    lines            = raw.strip().splitlines()
    records          = []
    current_category = ""
    current_amc      = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Category headers e.g. "Open Ended Schemes(Equity Scheme - ...)"
        if line.startswith("Open Ended") or line.startswith("Close Ended") or line.startswith("Interval"):
            current_category = line
            continue
        parts = line.split(";")
        if len(parts) < 7:
            # AMC name line (no semicolons, no leading digit)
            if not any(ch.isdigit() for ch in line[:3]):
                current_amc = line
            continue
        try:
            records.append({
                "scheme_code"       : int(parts[0].strip()),
                "isin_growth"       : parts[1].strip() or None,
                "isin_div_reinvest" : parts[2].strip() or None,
                "scheme_name"       : parts[3].strip(),
                "plan"              : parts[4].strip(),
                "option"            : parts[5].strip(),
                "nav"               : float(parts[6].strip()),
                "date"              : parts[7].strip() if len(parts) > 7 else None,
                "amc"               : current_amc,
                "category"          : current_category,
            })
        except (ValueError, IndexError):
            continue

    df = pd.DataFrame(records)
    print(f"  {len(df):,} schemes parsed from AMFI NAV file.")
    return df


def filter_amfi_nav(
    df: pd.DataFrame,
    amc: str = "",
    category: str = "",
    name: str = ""
) -> pd.DataFrame:
    """Filter the AMFI NAV DataFrame by AMC name, category keyword, or scheme name keyword."""
    if amc:
        df = df[df["amc"].str.contains(amc, case=False, na=False)]
    if category:
        df = df[df["category"].str.contains(category, case=False, na=False)]
    if name:
        df = df[df["scheme_name"].str.contains(name, case=False, na=False)]
    return df.reset_index(drop=True)


# =============================================================================
# MODULE 4 – Portfolio Holdings  (AMFI Monthly Disclosure)
# =============================================================================

def get_portfolio_holdings(scheme_code: int, month: str = None, year: int = None) -> pd.DataFrame:
    """
    Fetch the monthly portfolio holdings for an Indian mutual fund.

    AMFI publishes monthly portfolio disclosures. This function queries the
    AMFI portfolio module for the given scheme and returns a DataFrame with
    the portfolio holdings (securities, % allocation, market value, etc.).

    Parameters
    ----------
    scheme_code : int    AMFI scheme code
    month       : str    3-letter month e.g. "Jul" (defaults to last full month)
    year        : int    4-digit year e.g. 2024 (defaults to current year)

    Returns
    -------
    pd.DataFrame with portfolio security details and a 'month_year' column.
    """
    import calendar
    today = date.today()
    if month is None:
        prev_month = today.month - 1 if today.month > 1 else 12
        prev_year  = today.year if today.month > 1 else today.year - 1
        month      = calendar.month_abbr[prev_month]
        if year is None:
            year = prev_year
    if year is None:
        year = today.year

    month_year = f"{month}-{year}"
    print(f"\n[4] Fetching portfolio for scheme {scheme_code} ({month_year}) ...")

    payload = {
        "MFScheme": scheme_code,
        "Month"   : month_year,
    }
    raw = _get(AMFI_PORTFOLIO_URL, data=payload, method="POST")

    if not raw:
        print("  No data returned from AMFI portfolio endpoint.")
        _fallback_portfolio_notice()
        return pd.DataFrame()

    try:
        tables = pd.read_html(str(raw))
    except Exception as exc:
        print(f"  Could not parse AMFI portfolio response: {exc}")
        _fallback_portfolio_notice()
        return pd.DataFrame()

    if not tables:
        print("  No tables found in AMFI portfolio response.")
        _fallback_portfolio_notice()
        return pd.DataFrame()

    # The main holdings table is usually the largest one
    df = max(tables, key=len)
    df.columns = [str(c).strip() for c in df.columns]

    # Standardise common column names
    rename_map = {}
    for col in df.columns:
        low = col.lower()
        if "name" in low or "instrument" in low:
            rename_map[col] = "security_name"
        elif "isin" in low:
            rename_map[col] = "isin"
        elif "rating" in low:
            rename_map[col] = "rating"
        elif "market" in low and "value" in low:
            rename_map[col] = "market_value_lakhs"
        elif "%" in low or "nav" in low or "corpus" in low:
            rename_map[col] = "pct_of_nav"
        elif "sector" in low:
            rename_map[col] = "sector"
        elif "type" in low:
            rename_map[col] = "instrument_type"
    df.rename(columns=rename_map, inplace=True)
    df["month_year"] = month_year
    df.dropna(how="all", inplace=True)
    df.reset_index(drop=True, inplace=True)
    print(f"  {len(df)} portfolio rows fetched.")
    return df


def _fallback_portfolio_notice():
    print(
        "\n  NOTE: Portfolio holdings require AMFI portal access.\n"
        "  If blocked, download manually from:\n"
        "    https://www.amfiindia.com/research-information/other-data/\n"
        "  Then use parse_amfi_portfolio_excel(filepath) in this script.\n"
    )


def parse_amfi_portfolio_excel(filepath: str) -> pd.DataFrame:
    """
    Parse a manually downloaded AMFI portfolio Excel/CSV file.
    Supports .xlsx and .csv formats.

    Download from:
      https://www.amfiindia.com/research-information/other-data/
      -> 'Monthly Portfolio for All AMCs' -> download Excel
    """
    print(f"\n[4b] Parsing local portfolio file: {filepath} ...")
    if not os.path.exists(filepath):
        print(f"  File not found: {filepath}")
        return pd.DataFrame()

    ext = os.path.splitext(filepath)[-1].lower()
    try:
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(filepath)
        elif ext == ".csv":
            df = pd.read_csv(filepath, encoding="utf-8-sig")
        else:
            print(f"  Unsupported file format: {ext}")
            return pd.DataFrame()
    except Exception as exc:
        print(f"  Failed to read file: {exc}")
        return pd.DataFrame()

    print(f"  {len(df):,} rows loaded from local file.")
    return df


# =============================================================================
# MODULE 5 – NAV Analytics (returns, stats)
# =============================================================================

def compute_returns(df_nav: pd.DataFrame) -> dict:
    """
    Given a NAV history DataFrame (columns: date, nav), compute:
      - 1D, 1W, 1M, 3M, 6M, 1Y, 3Y, 5Y, 10Y absolute returns & CAGR
      - All-time high / low NAV
    """
    if df_nav.empty or "nav" not in df_nav.columns:
        return {}

    df          = df_nav.sort_values("date").reset_index(drop=True)
    latest_date = df["date"].iloc[-1]
    latest_nav  = df["nav"].iloc[-1]

    def nav_on_or_before(days_ago: int) -> Optional[float]:
        target = latest_date - pd.Timedelta(days=days_ago)
        subset = df[df["date"] <= target]
        return subset.iloc[-1]["nav"] if not subset.empty else None

    def cagr(old: float, new: float, years: float) -> float:
        return ((new / old) ** (1 / years) - 1) * 100

    periods = {
        "1D" : 1,  "1W" : 7,  "1M" : 30,   "3M" : 90,
        "6M" : 180, "1Y": 365, "3Y" : 365*3, "5Y" : 365*5, "10Y": 365*10,
    }

    returns = {}
    for label, days in periods.items():
        old = nav_on_or_before(days)
        if old and old > 0:
            abs_ret  = ((latest_nav - old) / old) * 100
            years    = days / 365
            cagr_ret = cagr(old, latest_nav, years) if years >= 1 else None
            returns[label] = {
                "absolute_%": round(abs_ret, 2),
                "cagr_%"    : round(cagr_ret, 2) if cagr_ret else None,
                "nav_then"  : round(old, 4),
                "nav_now"   : round(latest_nav, 4),
            }

    return {
        "latest_nav"    : round(latest_nav, 4),
        "latest_date"   : str(latest_date.date()),
        "all_time_high" : round(df["nav"].max(), 4),
        "all_time_low"  : round(df["nav"].min(), 4),
        "returns"       : returns,
    }


# =============================================================================
# MODULE 6 – AMC / Category Summary
# =============================================================================

def get_amc_summary(df_amfi: pd.DataFrame) -> pd.DataFrame:
    """Group AMFI NAV data by AMC – scheme count, avg/max/min NAV."""
    if df_amfi.empty:
        return pd.DataFrame()
    return (
        df_amfi.groupby("amc")
        .agg(num_schemes=("scheme_code","count"), avg_nav=("nav","mean"),
             max_nav=("nav","max"), min_nav=("nav","min"))
        .round(2)
        .sort_values("num_schemes", ascending=False)
        .reset_index()
    )


def get_category_summary(df_amfi: pd.DataFrame) -> pd.DataFrame:
    """Group AMFI NAV data by SEBI category."""
    if df_amfi.empty:
        return pd.DataFrame()
    return (
        df_amfi.groupby("category")
        .agg(num_schemes=("scheme_code","count"))
        .sort_values("num_schemes", ascending=False)
        .reset_index()
    )


# =============================================================================
# MAIN – Demonstration runner
# =============================================================================

def main():
    ensure_output_dir()
    print("=" * 70)
    print("   Indian Mutual Fund Data Extractor")
    print("   Sources: mfapi.in  |  AMFI India")
    print("=" * 70)

    # -- 1. Master fund list --------------------------------------------------
    df_all_funds = get_all_funds()
    if not df_all_funds.empty:
        save_csv(df_all_funds, "all_funds_master.csv")

    # -- 2. Search demo -------------------------------------------------------
    print("\n" + "-" * 70)
    print("SEARCH: 'Mirae Asset Large Cap'")
    df_search = search_funds("Mirae Asset Large Cap", df_all_funds)
    if not df_search.empty:
        _print_table(df_search, max_rows=10)
        save_csv(df_search, "search_mirae_large_cap.csv")

    # -- 3. NAV history + analytics for one scheme ---------------------------
    SAMPLE_SCHEME = 119598   # Mirae Asset Large Cap Fund – Direct Plan – Growth

    print("\n" + "-" * 70)
    details = get_fund_details(SAMPLE_SCHEME)
    if details:
        save_json(details["meta"], f"scheme_{SAMPLE_SCHEME}_meta.json")

        df_nav = pd.DataFrame(details.get("data", []))
        df_nav["date"] = pd.to_datetime(df_nav["date"], format="%d-%m-%Y")
        df_nav["nav"]  = df_nav["nav"].astype(float)
        df_nav.sort_values("date", inplace=True)
        save_csv(df_nav, f"scheme_{SAMPLE_SCHEME}_nav_history.csv")

        analytics = compute_returns(df_nav)
        print(f"\n  Latest NAV    : Rs {analytics.get('latest_nav')}  ({analytics.get('latest_date')})")
        print(f"  All-time High : Rs {analytics.get('all_time_high')}")
        print(f"  All-time Low  : Rs {analytics.get('all_time_low')}")
        print("\n  Returns:")
        rows = [
            {"Period": k, "Absolute %": v["absolute_%"], "CAGR %": v.get("cagr_%", "-"),
             "NAV Then": v["nav_then"], "NAV Now": v["nav_now"]}
            for k, v in analytics.get("returns", {}).items()
        ]
        _print_table(pd.DataFrame(rows), max_rows=20)
        save_json(analytics, f"scheme_{SAMPLE_SCHEME}_analytics.json")

    # -- 4. AMFI live NAV (all schemes) -------------------------------------
    print("\n" + "-" * 70)
    df_amfi = get_amfi_all_nav()
    if not df_amfi.empty:
        save_csv(df_amfi, "amfi_all_nav_live.csv")

        df_amc = get_amc_summary(df_amfi)
        print("\n  Top 10 AMCs by scheme count:")
        _print_table(df_amc, max_rows=10)
        save_csv(df_amc, "amc_summary.csv")

        df_cat = get_category_summary(df_amfi)
        print("\n  Schemes by SEBI Category:")
        _print_table(df_cat, max_rows=30)
        save_csv(df_cat, "category_summary.csv")

        print("\n  Filter: Mirae Asset | Equity schemes")
        df_filtered = filter_amfi_nav(df_amfi, amc="Mirae", category="Equity")
        if not df_filtered.empty:
            _print_table(df_filtered[["scheme_code","scheme_name","plan","nav","date"]], 15)
            save_csv(df_filtered, "mirae_equity_nav.csv")

    # -- 5. Portfolio holdings -----------------------------------------------
    print("\n" + "-" * 70)
    df_portfolio = get_portfolio_holdings(SAMPLE_SCHEME)
    if not df_portfolio.empty:
        _print_table(df_portfolio, max_rows=20)
        save_csv(df_portfolio, f"scheme_{SAMPLE_SCHEME}_portfolio.csv")
        save_json(df_portfolio.to_dict(orient="records"), f"scheme_{SAMPLE_SCHEME}_portfolio.json")

    # -- 6. Compare top large-cap funds --------------------------------------
    print("\n" + "-" * 70)
    print("COMPARING TOP LARGE CAP DIRECT GROWTH FUNDS ...")
    COMPARE_SCHEMES = {
        119598 : "Mirae Asset Large Cap – Direct G",
        120503 : "Axis Bluechip – Direct G",
        120465 : "ICICI Pru Bluechip – Direct G",
        125354 : "SBI Bluechip – Direct G",
    }
    compare_rows = []
    for code, label in COMPARE_SCHEMES.items():
        nav = get_current_nav(code)
        if nav:
            compare_rows.append({"Scheme": label, "Scheme Code": code, "Current NAV (Rs)": nav})
        time.sleep(0.5)

    if compare_rows:
        df_compare = pd.DataFrame(compare_rows)
        _print_table(df_compare)
        save_csv(df_compare, "large_cap_nav_comparison.csv")

    print("\n" + "=" * 70)
    print(f"  All outputs saved to: ./{OUTPUT_DIR}/")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Quick-lookup CLI mode:  python indian_mf_extractor.py <scheme_code>
# ---------------------------------------------------------------------------

def quick_lookup(scheme_code: int):
    """Print all key data for a single scheme (CLI mode)."""
    ensure_output_dir()
    details = get_fund_details(scheme_code)
    if not details:
        return

    df_nav = pd.DataFrame(details.get("data", []))
    if not df_nav.empty:
        df_nav["date"] = pd.to_datetime(df_nav["date"], format="%d-%m-%Y")
        df_nav["nav"]  = df_nav["nav"].astype(float)
        df_nav.sort_values("date", inplace=True)

    analytics = compute_returns(df_nav)

    print(f"\n  {'─'*60}")
    print(f"  Fund : {details['meta'].get('scheme_name')}")
    print(f"  AMC  : {details['meta'].get('fund_house')}")
    print(f"  Cat  : {details['meta'].get('scheme_category')}")
    print(f"  ISIN : {details['meta'].get('isin_growth')}")
    print(f"  {'─'*60}")
    print(f"  Latest NAV    : Rs {analytics.get('latest_nav')}  ({analytics.get('latest_date')})")
    print(f"  All-time High : Rs {analytics.get('all_time_high')}")
    print(f"  All-time Low  : Rs {analytics.get('all_time_low')}")
    print("\n  Returns:")
    rows = [
        {"Period": k, "Absolute %": v["absolute_%"], "CAGR %": v.get("cagr_%", "-")}
        for k, v in analytics.get("returns", {}).items()
    ]
    _print_table(pd.DataFrame(rows), max_rows=20)

    portfolio = get_portfolio_holdings(scheme_code)
    if not portfolio.empty:
        print("\n  Top Holdings:")
        _print_table(portfolio, max_rows=10)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) == 2:
        try:
            quick_lookup(int(sys.argv[1]))
        except ValueError:
            print("Usage: python indian_mf_extractor.py <scheme_code>")
    else:
        main()
