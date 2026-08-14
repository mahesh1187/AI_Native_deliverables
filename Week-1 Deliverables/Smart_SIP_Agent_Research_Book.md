# 📘 Smart SIP Agent
## A Research Book on AI-Native Dynamic Investment Systems for Retail Investors

---

> **Author:** Mahesh | AI-Native Learning Program — Week 1 Deliverable
> **Date:** August 2026
> **Classification:** Research & Product Design Document
> **Domain:** FinTech · Agentic AI · Investment Automation · Indian Capital Markets

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Market Landscape & Competitive Analysis](#3-market-landscape--competitive-analysis)
4. [Investment Strategy: The Science Behind Smart SIP](#4-investment-strategy-the-science-behind-smart-sip)
5. [Agent Architecture & Design](#5-agent-architecture--design)
6. [Core Technical Components](#6-core-technical-components)
7. [User Journey & Interaction Design](#7-user-journey--interaction-design)
8. [Data Model](#8-data-model)
9. [Technology Stack](#9-technology-stack)
10. [Regulatory & Compliance Framework (India)](#10-regulatory--compliance-framework-india)
11. [AI Agent Design Principles](#11-ai-agent-design-principles)
12. [MVP Roadmap](#12-mvp-roadmap)
13. [Risk Register](#13-risk-register)
14. [Success Metrics & KPIs](#14-success-metrics--kpis)
15. [Glossary](#15-glossary)
16. [References & Further Reading](#16-references--further-reading)

---

## 1. Executive Summary

Most retail investors in India use a **Systematic Investment Plan (SIP)** — a fixed, automated monthly contribution to a mutual fund or ETF. While this strategy enforces discipline and leverages rupee cost averaging, it is **fundamentally blind to market conditions**. An investor who contributes Rs.5,000 every 1st of the month invests the same amount whether the market is at a historic high or a 3-month low.

The **Smart SIP Agent** solves this by introducing an AI-native layer on top of the traditional SIP. The agent continuously monitors market signals, detects buying opportunities (dips), and either automatically executes additional investments or notifies the investor with a clear, explainable recommendation — all within their pre-configured budget.

This research book covers:
- The exact problem and why it matters for ~60 million SIP investors in India
- Competitive landscape and the existing gap
- The investment science underpinning the system
- A full technical architecture for building the agent
- India-specific regulatory compliance requirements
- A phased product roadmap from MVP to scale

---

## 2. Problem Statement

### 2.1 The Rigid SIP Problem

A standard SIP is set up as:

```
Investor sets: Rs.5,000 into HDFC Flexi Cap Fund on the 1st of every month
```

This is what happens across different market scenarios:

| Date | Nifty 50 Level | Market Condition | Action Taken |
|------|----------------|-----------------|--------------|
| Jun 1 | 24,500 | All-time high | Rs.5,000 invested |
| Jun 4 | 23,352 | -3.2% drop (opportunity!) | Nothing — next SIP is July 1 |
| Jul 1 | 24,100 | Recovered | Rs.5,000 invested |
| Aug 1 | 24,800 | New high | Rs.5,000 invested |

**The investor systematically misses every dip opportunity between their SIP dates.**

### 2.2 Why This Matters

- ~60 million active SIP accounts exist in India (AMFI, 2024)
- Average SIP ticket size: Rs.2,500 to Rs.7,000/month
- Nifty 50 sees intra-month dips of >2% approximately 6 to 8 times per year
- Historical data shows: Buying on dips of >3% yields, on average, +2.4% better 1-year returns vs fixed-date investing (source: Motilal Oswal research)

### 2.3 The Root Cause

| Problem Layer | Root Cause |
|---|---|
| **Behavioral** | Investors set-and-forget; don't monitor markets daily |
| **Structural** | Traditional SIP infrastructure doesn't support event-triggered orders |
| **Emotional** | When markets drop, most investors panic — they don't buy more |
| **Informational** | Investors lack real-time signals telling them "now is a good time to buy" |

### 2.4 The Opportunity — How the Agent Solves It

The Smart SIP Agent acts as an **always-on financial co-pilot** that:

1. **Monitors** market indices, fund NAVs, and technical indicators 24x5
2. **Scores** each market event using a multi-signal dip detection algorithm
3. **Notifies** the investor with a plain-language explanation
4. **Executes** a calculated additional investment within user-defined budget cap
5. **Reports** the impact of every smart buy vs. a baseline regular SIP

---

## 3. Market Landscape & Competitive Analysis

### 3.1 Existing Players

| Platform | Smart Feature | Execution Model | Gap |
|---|---|---|---|
| **CashRich** | Dynamic SIP using "Margin of Safety" index | Rule-based multiplier | No AI explainability; no conversational interface |
| **Stashfin** | Smart SIP — rule-based increase on dips | Fixed % increase | Binary logic; no multi-signal scoring |
| **Jarvis Invest** | AI portfolio management | SEBI RIA | Stock-focused; not SIP/MF native |
| **Groww** | AI insights, step-up SIP | Date-based only | No dip detection; no event-triggered execution |
| **ET Money Genius** | Portfolio recommendations | Advisory only | Not autonomous; manual action required |
| **5Paisa Smart SIP** | Multiplier SIP on dips | Up to 4x base amount | No explainability; no learning loop |
| **Zerodha Coin** | Direct SIP management | Date-based only | No intelligence layer at all |

### 3.2 Competitive Gap — Where We Win

None of the current platforms offer a **fully conversational, explainable AI agent** that:

1. Detects dips using **multi-signal intelligence** (not just % drop)
2. Notifies the investor with a **human-readable rationale** 
3. Allows **natural language overrides** ("skip this dip", "invest double")
4. Tracks the **impact of each smart buy** vs. a baseline SIP retrospectively
5. **Learns from user behavior** to improve recommendations over time

---

## 4. Investment Strategy: The Science Behind Smart SIP

### 4.1 Strategy Comparison

| Strategy | Amount | Timing | Complexity | Best For |
|---|---|---|---|---|
| **Regular SIP (Rupee Cost Averaging)** | Fixed | Fixed date | Low | Beginners, discipline-first |
| **Value Averaging** | Variable | Fixed date | High | Active investors with cash buffers |
| **Flexi SIP (Manual)** | Variable | Manual decision | Very High | Expert investors only |
| **Smart Dip SIP (Agent)** | Variable | Event-driven | Medium (agent handles complexity) | Tech-savvy, goal-driven investors |

### 4.2 The Smart SIP Investment Formula

The agent operates on a **tiered dip response model**:

```
Base SIP: Rs.5,000/month (always executes on scheduled date)

Bonus Buy Tiers (in addition to base SIP):
  Level 1: Market drops 2.0% to 3.0%  -> Extra Rs.2,500
  Level 2: Market drops 3.0% to 5.0%  -> Extra Rs.5,000
  Level 3: Market drops > 5.0%        -> Extra Rs.10,000 (requires explicit approval)

Monthly Budget Cap: Rs.15,000 (configurable)
Agent never exceeds this cap, regardless of dip size
```

### 4.3 Why This Works — Academic Basis

**Rupee Cost Averaging (RCA)** works because it buys more units when NAV is low. The Smart SIP amplifies this:

| Scenario | Regular SIP | Smart SIP |
|---|---|---|
| Normal month | 200 units @ Rs.25 NAV | 200 units @ Rs.25 NAV |
| Dip month (-3%) | 200 units @ Rs.24.25 NAV | 200 + 206 = 406 units @ Rs.24.25 NAV |
| Recovery (+5%) | Portfolio value higher | Portfolio value significantly higher |

**Key Finding:** Research by Motilal Oswal AMC shows dip-buying on Nifty 50 corrections of >3% produces an average **+2.4% excess CAGR** over a 5-year investment horizon.

### 4.4 Guard Rails — When the Agent Does NOT Buy

The agent incorporates **bear market protection**:

- Nifty 50 is below its 200-day SMA (indicates structural bear market — avoid buying falling knives)
- India VIX > 30 (extreme fear — wait for stabilization)
- Monthly budget cap already reached (spend discipline)
- User has manually paused the agent (user control always respected)
- Market is in a circuit breaker halt (system protection)

---

## 5. Agent Architecture & Design

### 5.1 High-Level Architecture

```
PERCEPTION LAYER         REASONING LAYER          ACTION LAYER
-------------------    ----------------------    ------------------
Market Data Feed    ->  Dip Score Engine      ->  Execute Buy Order
Fund NAV               Risk Profile Match         Send Notification
RSI + SMA + VIX        Budget Cap Check           Log Decision
                        Bear Mkt Guard             Update Dashboard
                        LLM Explainer              Learn from Feedback
```

### 5.2 Agent Decision Flowchart

```
Market Opens (9:15 AM IST)
         |
         v
  Fetch Live Data  <-- Nifty50, VIX, RSI, SMA200, Fund NAV
         |
         v
  Compute Dip Score  <-- Weighted multi-signal scoring
         |
    Score < Threshold?
    --------+--------
   YES               NO
    |                 |
  Log:           Compute Bonus Amount
  No Action      (based on tier)
    |                 |
    |           Check Budget Cap
    |                 |
    |           Cap Exceeded?
    |           ----+----
    |          YES       NO
    |           |         |
    |         Log:    Check Approval Mode
    |         Skip         |
    |               -------+-------
    |           AUTO-APPROVE    NOTIFY USER
    |               |                |
    |           Execute         WhatsApp + Push
    |           Order           Notification
    |               |                |
    |               |           User Responds
    |               |          ------+------
    |               |       Approve     Skip/Modify
    |               |          |              |
    +---------------+----------+--------------+
                               |
                   Post-Trade: Log + Dashboard Update
                   + Compute vs Baseline SIP delta
```

### 5.3 The Decision Card (Explainability)

Every agent decision generates a **Decision Card** — a structured, human-readable explanation sent via WhatsApp or in-app:

```
SMART SIP OPPORTUNITY DETECTED
Thursday, 15 Aug 2026 — 11:42 AM

WHAT HAPPENED
  Nifty 50:   24,120 -> 23,352  (-3.2%)
  RSI (14d):  28.4  -> Oversold zone (below 35)
  200d SMA:   22,840 -> Price still ABOVE (bull trend intact)
  India VIX:  17.2  -> Normal fear level
  Fund NAV:   Rs.142.30 -> Rs.138.40  (-2.7%)

AGENT REASONING
  Dip Score: 78/100 (Level 2 Trigger)
  This is a statistically significant buying opportunity.
  Last 3 times this signal fired: avg +14.2% return over 6 months.

RECOMMENDATION
  Extra buy: Rs.5,000 in HDFC Flexi Cap Fund
  (Rs.3,500 remaining in your monthly budget cap)

  [Approve Rs.5,000]   [Modify Amount]   [Skip This Time]
```

---

## 6. Core Technical Components

### 6.1 Market Data Layer

| Signal | Data Source | Frequency | Purpose |
|---|---|---|---|
| **Index Level** (Nifty 50, Sensex, MidCap) | TrueData / NSEPython | Real-time WebSocket | Detect % drop from recent high |
| **RSI (14-day)** | Computed from OHLC data | Daily close | Identify oversold conditions |
| **200-day SMA** | Computed from historical data | Daily | Confirm long-term bull trend |
| **India VIX** | NSE API | Real-time | Measure fear/volatility |
| **Fund NAV** | AMFI Daily NAV API | End-of-day | Fund-specific dip detection |
| **P/E Ratio** | NSE / Nifty PE data | Daily | Valuations context |

**API Priority Hierarchy:**
```
Production : TrueData (paid, low-latency WebSocket for NSE/BSE)
Fallback 1 : NSEPython (free, NSE website scraper)
Fallback 2 : yfinance (prototyping only, not production-grade)
```

### 6.2 Dip Detection Algorithm (Python)

```python
from dataclasses import dataclass

@dataclass
class MarketSnapshot:
    index_close: float
    index_52w_high: float
    rsi_14: float
    sma_200: float
    vix: float
    fund_nav: float
    fund_nav_3d_ago: float

def compute_dip_score(snapshot: MarketSnapshot, risk_profile: str) -> float:
    """
    Returns a score 0-100 representing buying opportunity strength.
    Multi-signal weighted scoring based on investor risk profile.
    """
    weights = {
        "conservative": {"price": 0.30, "rsi": 0.25, "sma": 0.30, "vix": 0.10, "nav": 0.05},
        "moderate":     {"price": 0.35, "rsi": 0.25, "sma": 0.20, "vix": 0.10, "nav": 0.10},
        "aggressive":   {"price": 0.40, "rsi": 0.20, "sma": 0.15, "vix": 0.05, "nav": 0.20},
    }
    w = weights[risk_profile]

    # Signal 1: Price drop from 52-week high
    price_drop = (snapshot.index_52w_high - snapshot.index_close) / snapshot.index_52w_high * 100
    price_score = min(price_drop / 2.0 * 50, 100)  # 2% = threshold

    # Signal 2: RSI oversold (RSI < 35 fires signal)
    rsi_score = max(0, (35 - snapshot.rsi_14) / 35 * 100) if snapshot.rsi_14 < 35 else 0

    # Signal 3: Above 200-day SMA (bull trend = green light to buy)
    sma_score = 100 if snapshot.index_close > snapshot.sma_200 else 0

    # Signal 4: VIX — moderate fear OK, extreme fear = wait
    vix_score = 100 if snapshot.vix < 25 else (50 if snapshot.vix < 30 else 0)

    # Signal 5: Fund-specific NAV drop (last 3 days)
    nav_drop = (snapshot.fund_nav_3d_ago - snapshot.fund_nav) / snapshot.fund_nav_3d_ago * 100
    nav_score = min(nav_drop / 1.5 * 100, 100) if nav_drop > 0 else 0

    final_score = (
        w["price"] * price_score +
        w["rsi"]   * rsi_score   +
        w["sma"]   * sma_score   +
        w["vix"]   * vix_score   +
        w["nav"]   * nav_score
    )
    return round(final_score, 2)


def get_bonus_amount(score: float, tiers: dict) -> dict:
    """Maps dip score to investment tier and bonus amount."""
    if score >= 75:
        return {"level": 3, "amount": tiers["level_3"]["extra_invest"],
                "needs_approval": tiers["level_3"]["needs_approval"]}
    elif score >= 50:
        return {"level": 2, "amount": tiers["level_2"]["extra_invest"], "needs_approval": False}
    elif score >= 30:
        return {"level": 1, "amount": tiers["level_1"]["extra_invest"], "needs_approval": False}
    return {"level": 0, "amount": 0, "needs_approval": False}
```

### 6.3 Execution Layer — India-Specific

**Critical Constraint:** India's mutual fund ecosystem has specific execution pathways. Fully programmatic MF order execution requires regulated access.

| Asset Type | Execution Route | API | Regulatory Requirement |
|---|---|---|---|
| **ETFs** (Nifty BeES, Nippon Nifty ETF) | Stock broker order | Zerodha Kite API | Broker demat account |
| **Direct MF** | BSE StarMF platform | BSE StarMF API | AMFI ARN registration |
| **Regular MF** | Distributor route | MFU / CAMS API | AMFI ARN + distributor empanelment |

**Recommended MVP Execution Path:**

```
Phase 1 (MVP): ETF route via Zerodha Kite API
  -> Buy Nifty BeES or equivalent ETF on NSE
  -> Full programmatic support; no MF-specific licensing needed
  -> Real-time order confirmation available

Phase 2 (Scale): BSE StarMF API for direct mutual funds
  -> Requires AMFI ARN registration
  -> Support for all AMCs (HDFC, Mirae, Axis, etc.)
  -> e-NACH mandate for automated bank debit
```

**Zerodha Kite API — ETF Execution:**

```python
from kiteconnect import KiteConnect

kite = KiteConnect(api_key="your_api_key")
kite.set_access_token("your_access_token")

def place_smart_buy(symbol: str, amount_inr: float) -> dict:
    """Places a CNC market order for ETF on a dip signal."""
    ltp = kite.ltp(f"NSE:{symbol}")[f"NSE:{symbol}"]["last_price"]
    quantity = int(amount_inr // ltp)  # whole units only

    if quantity < 1:
        return {"status": "error", "reason": "Amount too small for 1 unit"}

    order_id = kite.place_order(
        tradingsymbol=symbol,
        exchange="NSE",
        transaction_type="BUY",
        quantity=quantity,
        order_type="MARKET",
        product="CNC",     # delivery/long-term holding
        variety="regular"
    )
    return {"status": "success", "order_id": order_id, "qty": quantity, "ltp": ltp}
```

### 6.4 Notification Engine

| Channel | Open Rate | Use Case |
|---|---|---|
| **WhatsApp** (360dialog) | ~85-95% | Primary: dip alerts + approval requests |
| **Push Notification** (Firebase FCM) | ~40-60% | Secondary: confirmations, summaries |
| **Email** | ~20-30% | Monthly performance reports |
| **In-App** | ~100% when open | Real-time dashboard updates |

### 6.5 Analytics & Retrospective Engine

After each smart buy, the agent tracks performance:

```
Smart Buy Record:
  - Date and time of execution
  - Fund/ETF name and NAV at purchase
  - Units purchased + amount invested
  - Dip score + level that triggered the buy
  - Baseline: what regular SIP would have bought (NAV on scheduled date)
  - Delta: computed at 1 month, 3 month, 6 month, 12 month marks
```

**Sample Monthly Retrospective Report:**

```
YOUR SMART SIP PERFORMANCE — AUGUST 2026
-------------------------------------------
Regular SIP invested:        Rs.5,000  (1st Aug @ NAV Rs.142.30)
Smart buys this month:       Rs.5,000  (15th Aug @ NAV Rs.138.40)
Total invested this month:   Rs.10,000

Avg NAV paid (Smart SIP):    Rs.140.35
Avg NAV paid (Regular only): Rs.142.30

Savings per unit:            Rs.1.95
Units bought cheaper:        +4.7 units
Estimated 1-year impact:     +Rs.1,240 (at 12% expected growth)
-------------------------------------------
Cumulative Smart Advantage:  +Rs.3,480 (since Jan 2026)
```

---

## 7. User Journey & Interaction Design

### 7.1 Onboarding Flow (5 Steps)

```
Step 1 | IDENTITY VERIFICATION
       | PAN + Aadhaar via DigiLocker API
       | CKYC lookup to auto-fill profile

Step 2 | LINK YOUR INVESTMENT ACCOUNT
       | Options: Zerodha Coin / Groww / MFCentral folio number
       | Read-only access first (view holdings, existing SIPs)

Step 3 | SET BASE SIP PREFERENCES
       | Fund/ETF selection
       | Base amount (Rs.)
       | Existing SIP date

Step 4 | CONFIGURE SMART SIP RULES
       | Dip thresholds (pre-set profiles: Conservative / Balanced / Aggressive)
       | Monthly budget cap
       | Auto-approve limit (e.g., auto-approve up to Rs.5,000, ask above)

Step 5 | SET NOTIFICATION PREFERENCES
       | WhatsApp number verification
       | Preferred channel (WhatsApp / App / Email)
       | Quiet hours setting

       AGENT ACTIVATED
```

### 7.2 Daily Agent Operation

```
9:15 AM   Market opens. Agent begins monitoring.
          (Investor is at work, not watching markets)

11:30 AM  Agent detects: Nifty drops 3.2%, RSI = 28, score = 78
          Computes: Level 2 trigger -> Rs.5,000 extra buy
          Budget check: Rs.8,500 remaining this month - OK

11:31 AM  WhatsApp notification sent with Decision Card

11:46 AM  Investor reads notification, replies "YES"

11:46 AM  Agent executes buy order
          Confirmation: "Rs.5,000 invested in HDFC Flexi Cap"
          Dashboard updated with "Smart Buy" marker

End of Month: Performance report: Smart buys vs baseline SIP comparison
```

### 7.3 Dashboard UX Design Principles

| Principle | Implementation |
|---|---|
| **Goal-first, not data-first** | Show "Rs.2.4L closer to your Rs.10L goal" not raw NAV numbers |
| **Progressive disclosure** | Summary view -> tap for details -> see raw signals |
| **Human control always visible** | "Pause Agent" button always accessible |
| **Explain every action** | Every smart buy has "Why did the agent do this?" link |
| **Emotional reassurance** | During market crashes: "Your agent is prepared — here's the plan" |
| **Celebrate wins** | "Your 3 smart buys earned Rs.1,240 extra this quarter" |

---

## 8. Data Model

### 8.1 Core Database Schema

```sql
-- User Profile
CREATE TABLE users (
    id              UUID PRIMARY KEY,
    name            TEXT NOT NULL,
    pan             TEXT UNIQUE NOT NULL,
    phone           TEXT,
    risk_profile    TEXT CHECK (risk_profile IN ('conservative','moderate','aggressive')),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- SIP Configuration
CREATE TABLE sip_configs (
    id                  UUID PRIMARY KEY,
    user_id             UUID REFERENCES users(id),
    fund_name           TEXT NOT NULL,
    isin                TEXT,
    base_amount         INTEGER NOT NULL,
    sip_date            INTEGER CHECK (sip_date BETWEEN 1 AND 28),
    monthly_cap         INTEGER NOT NULL,
    auto_approve_limit  INTEGER DEFAULT 0,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Dip Threshold Rules (per user per SIP)
CREATE TABLE dip_rules (
    id              UUID PRIMARY KEY,
    sip_config_id   UUID REFERENCES sip_configs(id),
    level           INTEGER CHECK (level IN (1,2,3)),
    min_drop_pct    DECIMAL(5,2),
    extra_amount    INTEGER,
    needs_approval  BOOLEAN DEFAULT FALSE
);

-- Market Events Detected by Agent
CREATE TABLE market_events (
    id              UUID PRIMARY KEY,
    event_type      TEXT DEFAULT 'dip',
    index_name      TEXT,
    drop_pct        DECIMAL(5,2),
    rsi_value       DECIMAL(5,2),
    sma_200         DECIMAL(10,2),
    vix_value       DECIMAL(5,2),
    dip_score       DECIMAL(5,2),
    detected_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Agent Decisions
CREATE TABLE agent_decisions (
    id                  UUID PRIMARY KEY,
    user_id             UUID REFERENCES users(id),
    event_id            UUID REFERENCES market_events(id),
    sip_config_id       UUID REFERENCES sip_configs(id),
    level               INTEGER,
    recommended_amount  INTEGER,
    rationale           TEXT,
    status              TEXT DEFAULT 'pending',
    user_response       TEXT,
    modified_amount     INTEGER,
    responded_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Trade Records
CREATE TABLE trade_records (
    id              UUID PRIMARY KEY,
    decision_id     UUID REFERENCES agent_decisions(id),
    user_id         UUID REFERENCES users(id),
    fund_name       TEXT,
    amount_inr      INTEGER,
    nav_at_purchase DECIMAL(10,4),
    units_bought    DECIMAL(12,4),
    trigger_type    TEXT,
    order_id        TEXT,
    executed_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Retrospective Performance Analytics
CREATE TABLE trade_retrospective (
    id                      UUID PRIMARY KEY,
    trade_id                UUID REFERENCES trade_records(id),
    period_months           INTEGER,
    nav_at_period           DECIMAL(10,4),
    return_pct              DECIMAL(7,4),
    vs_baseline_delta_inr   DECIMAL(12,2),
    computed_at             TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 9. Technology Stack

### 9.1 Full Stack Recommendation

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend — Web** | Next.js 14 | SSR for real-time dashboards; App Router |
| **Frontend — Mobile** | React Native (Expo) | Single codebase for iOS + Android |
| **Backend API** | FastAPI (Python) | Async-first; ML/AI ecosystem native |
| **Agent Orchestration** | LangGraph | Multi-step stateful agent pipelines |
| **LLM (Rationale Generation)** | Gemini 1.5 Pro | Plain-language explanation per decision |
| **Market Data** | TrueData API | Low-latency NSE/BSE WebSocket feed |
| **Database** | PostgreSQL 16 | ACID compliance for financial transactions |
| **Cache + Queue** | Redis + Celery | Real-time cache + async monitoring jobs |
| **Notifications** | 360dialog WhatsApp API + Firebase FCM | High open rate for financial alerts |
| **Order Execution (ETF)** | Zerodha Kite Connect | MVP: ETF programmatic execution |
| **Order Execution (MF)** | BSE StarMF API | Phase 2: full MF order placement |
| **Auth** | Supabase Auth | Row-Level Security; fast setup |
| **Hosting** | AWS ap-south-1 | India region; low latency for NSE |
| **Monitoring** | Grafana + Prometheus | Real-time agent health + trade monitoring |

### 9.2 Agent Pipeline (LangGraph)

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class AgentState(TypedDict):
    market_snapshot: dict
    user_config: dict
    dip_score: float
    bonus_amount: int
    rationale: str
    decision_status: str

# Node definitions
def fetch_market_data(state: AgentState) -> AgentState: ...
def compute_dip_score(state: AgentState) -> AgentState: ...
def generate_rationale(state: AgentState) -> AgentState: ...
def notify_user(state: AgentState) -> AgentState: ...
def execute_order(state: AgentState) -> AgentState: ...

def check_approval_mode(state: AgentState) -> str:
    if state["bonus_amount"] <= state["user_config"]["auto_approve_limit"]:
        return "execute"
    return "notify"

# Build graph
graph = StateGraph(AgentState)
graph.add_node("fetch_data",    fetch_market_data)
graph.add_node("score_dip",     compute_dip_score)
graph.add_node("gen_rationale", generate_rationale)
graph.add_node("notify",        notify_user)
graph.add_node("execute",       execute_order)

graph.set_entry_point("fetch_data")
graph.add_edge("fetch_data",    "score_dip")
graph.add_edge("score_dip",     "gen_rationale")
graph.add_conditional_edges("gen_rationale", check_approval_mode,
                             {"execute": "execute", "notify": "notify"})
graph.add_edge("notify",  "execute")
graph.add_edge("execute", END)

agent = graph.compile()
```

---

## 10. Regulatory & Compliance Framework (India)

### 10.1 Applicable Regulations

| Regulation | Body | Applicability |
|---|---|---|
| SEBI (Investment Advisers) Regulations, 2013 | SEBI | Personalized investment advice |
| SEBI (Mutual Funds) Regulations, 1996 | SEBI | MF distribution |
| SEBI Algo Trading Framework (April 2026) | SEBI / Exchanges | All automated order execution |
| AMFI Code of Conduct | AMFI | Mutual fund distribution |
| Prevention of Money Laundering Act (PMLA) | FIU-IND | KYC/AML obligations |
| IT Act 2000 + DPDPA 2023 | MeitY | Data protection |
| RBI Payment Guidelines | RBI | e-NACH / UPI mandates |

### 10.2 Compliance Checklist

| Requirement | Action Needed |
|---|---|
| SEBI Registered Investment Adviser (RIA) | Apply or partner with a SEBI-registered RIA |
| AMFI ARN (Mutual Fund Distributor) | Pass NISM V-A exam + apply for ARN |
| BSE StarMF Membership | Apply via BSE for MF execution access |
| SEBI Algo ID | Register each strategy with the stock exchange |
| KYC Integration | Integrate DigiLocker + CKYC central registry |
| e-NACH / UPI Mandate | Partner with payment aggregator (Razorpay/PayU) |
| WhatsApp Business API (WABA) | Apply via 360dialog/Interakt for official WABA |
| Cybersecurity (CSCRF) | Implement SEBI-mandated cybersecurity controls |
| Grievance Redressal | Designate SEBI-compliant grievance officer |

### 10.3 SEBI Algo Trading (April 2026) — Key Mandates

From SEBI's mandatory framework effective April 1, 2026:

1. **Exchange Approval** — Every trading algorithm must be approved before live deployment
2. **Unique Algo ID** — Every automated order must be tagged with a registered Unique Algo ID
3. **Broker Responsibility** — Brokers are the primary responsible party for algo compliance
4. **OPS Threshold** — Orders Per Second limits apply to retail algorithms
5. **Audit Trail** — Full logs of all algorithm decisions must be maintained for inspection

**MVP Compliance Path:**
Partner with a SEBI-RIA registered entity for the advice layer, use a registered broker's API for execution, and ensure all strategies have exchange-approved Algo IDs before go-live.

---

## 11. AI Agent Design Principles

### 11.1 Six Core Principles

**1. TRANSPARENCY**
Every action the agent takes is logged and explainable. No black-box decisions. The investor can always see why the agent made a recommendation.

**2. HUMAN CONTROL**
The investor is always in charge. The agent is an assistant, not an autonomous decision-maker. Pause, override, and modify controls are always available.

**3. PROGRESSIVE DISCLOSURE**
The dashboard shows what matters most, not everything. Simple summary -> Detailed view -> Raw technical signals — navigated on demand.

**4. EMOTIONAL INTELLIGENCE**
During market crashes, the agent is reassuring, not alarming. During gains, the agent celebrates with the investor. Language is calibrated to emotional context.

**5. LEARNING LOOP**
Every user decision (skip/approve/modify) teaches the agent about that investor's preferences and risk tolerance. The agent improves its recommendations over time.

**6. CONTEXTUAL RELEVANCE**
Alerts are sent only when meaningful to that specific investor's situation and goals. Agent avoids notification fatigue by limiting to 2-3 high-quality alerts per week maximum.

### 11.2 Human-in-the-Loop Spectrum

```
AGGRESSIVE MODE          BALANCED           ADVISORY         SAFE MODE
(Full Auto)              (Default)                           (Always Ask)
     |                       |                 |                  |
Agent executes       Agent executes       Agent notifies    Agent notifies
all buys auto        below limit;         for all buys;     but never
                     notifies above       user decides      executes without
                     threshold            each time         explicit approval
```

New users start in **Advisory Mode** and can graduate to Balanced or Aggressive mode after 30 days.

---

## 12. MVP Roadmap

### Phase 1 — Foundation (Months 1–3)

Goal: Core agent loop working end-to-end with manual approval

| Feature | Priority | Effort |
|---|---|---|
| User onboarding (KYC + account link) | P0 | High |
| Dashboard: portfolio view + SIP schedule | P0 | Medium |
| Market monitoring (Nifty 50 % dip, daily polling) | P0 | Medium |
| Basic dip score (price drop only for MVP) | P0 | Low |
| WhatsApp notification with Decision Card | P0 | Medium |
| Manual approval flow (reply YES/NO/MODIFY) | P0 | Low |
| ETF execution via Zerodha Kite API | P0 | High |
| Trade confirmation + basic dashboard update | P0 | Low |

**Success Criteria:** 100 beta users, agent correctly identifies and notifies on dips with <5 min latency

### Phase 2 — Intelligence (Months 4–6)

Goal: Multi-signal scoring + smart auto-execution

| Feature | Priority | Effort |
|---|---|---|
| Multi-signal dip score (RSI + SMA + VIX + NAV) | P0 | High |
| Auto-approval mode (below user threshold) | P0 | Medium |
| LLM-generated plain-language rationale | P1 | Medium |
| Backtesting simulator ("What if Smart SIP since Jan 2020?") | P1 | High |
| BSE StarMF integration (direct MF execution) | P1 | Very High |
| Smart buy retrospective analytics | P1 | Medium |

### Phase 3 — Personalization & Scale (Months 7–12)

Goal: Conversational AI + viral growth mechanics

| Feature | Priority | Effort |
|---|---|---|
| Conversational interface ("How did my SIP perform vs Sensex?") | P1 | High |
| AI risk profiling from behavior patterns | P2 | High |
| Multi-fund support (different dip rules per fund) | P1 | Medium |
| Portfolio rebalancing suggestions | P2 | High |
| Annual Smart SIP vs Regular SIP comparison report | P1 | Medium |
| Social proof: "Your Smart SIP outperformed X% of regular SIPs" | P2 | Low |
| Referral program | P2 | Low |

---

## 13. Risk Register

| Risk | Category | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| SEBI regulatory change on algo trading | Regulatory | Medium | High | Maintain SEBI RIA partnership; apply for regulatory sandbox |
| Market data API downtime | Technical | Medium | High | Multi-source fallback (TrueData -> NSEPython -> yfinance) |
| User over-trusts agent; over-invests | Behavioral | High | Medium | Hard monthly caps; mandatory confirmation for Level 3 buys |
| Extended bear market (below 200 SMA) | Market | Low | Medium | Auto-disable dip-buying in confirmed bear; revert to base SIP |
| Zerodha API rate limits | Technical | Low | Medium | Exponential backoff + request queue |
| Low user engagement, ignoring notifications | Product | High | Medium | Optimize timing; limit to 2-3 alerts/week max |
| Data breach / investor financial data leak | Security | Low | Very High | End-to-end encryption; CSCRF compliance; regular pen testing |
| WhatsApp approval spoofing | Security | Low | High | OTP verification + signed approval tokens |

---

## 14. Success Metrics & KPIs

### Product Metrics

| Metric | 6-Month Target | 12-Month Target |
|---|---|---|
| MAU (Monthly Active Users) | 2,000 | 10,000 |
| Notification Open Rate (WhatsApp) | >70% | >75% |
| Dip Opportunity Capture Rate | >75% | >85% |
| User Approval Rate (trust signal) | >65% | >72% |
| Average Time-to-Approve | <15 min | <10 min |

### Financial Metrics

| Metric | 6-Month Target | 12-Month Target |
|---|---|---|
| AUM via Smart SIP | Rs.2 Crore | Rs.10 Crore |
| Avg Smart SIP Outperformance vs Regular SIP | +1.5% CAGR | +2.5% CAGR |
| Platform Revenue (0.5% fee) | Rs.1L/month | Rs.5L/month |

### Agent Quality Metrics

| Metric | Description | Target |
|---|---|---|
| False Positive Rate | Dip signal fired but not a real opportunity | <15% |
| Signal Latency | Time from market dip to notification | <5 min |
| Execution Success Rate | Orders successfully placed | >99% |
| Retrospective Accuracy | Smart buys that outperformed baseline | >70% |

---

## 15. Glossary

| Term | Definition |
|---|---|
| **SIP** | Systematic Investment Plan — a fixed, recurring investment in a mutual fund |
| **NAV** | Net Asset Value — the per-unit price of a mutual fund |
| **RSI** | Relative Strength Index — momentum oscillator (0-100; below 30 = oversold) |
| **SMA** | Simple Moving Average — average closing price over N trading days |
| **VIX** | Volatility Index — measures market expectation of near-term volatility |
| **AMC** | Asset Management Company — entity managing a mutual fund (e.g., HDFC AMC) |
| **AMFI** | Association of Mutual Funds in India |
| **ARN** | AMFI Registration Number — required for distributing mutual funds |
| **BSE StarMF** | BSE's Mutual Fund transaction platform — standard API for programmatic MF orders |
| **RIA** | Registered Investment Adviser — SEBI-registered entity for personalized advice |
| **e-NACH** | Electronic National Automated Clearing House — bank debit mandate for recurring payments |
| **LangGraph** | Library for building stateful, multi-step AI agent pipelines |
| **WABA** | WhatsApp Business API — official API for automated business messaging |
| **CSCRF** | Cyber Security and Cyber Resilience Framework — SEBI-mandated cybersecurity standards |
| **Dip Score** | Proprietary weighted score (0-100) to evaluate buying opportunity strength |
| **RCA** | Rupee Cost Averaging — investing a fixed amount regularly regardless of price |
| **Value Averaging** | Investing variable amounts to hit a growing portfolio target value |
| **Circuit Breaker** | Market-wide trading halt triggered when index falls by a defined % |
| **CNC** | Cash and Carry — Zerodha's product code for delivery-based equity trades |
| **ISIN** | International Securities Identification Number — unique fund/stock identifier |

---

## 16. References & Further Reading

### Academic & Research Papers
- Edleson, M.E. (1991). *Value Averaging: The Safe and Easy Strategy for Higher Investment Returns*. International Publishing Corp.
- Motilal Oswal AMC (2023). *Dip-Buying on Nifty 50 — A 20-Year Retrospective Study*
- SEBI Working Paper: *Algorithmic Trading in Indian Capital Markets* (2023)

### Regulatory Documents
- SEBI Master Circular for Mutual Funds (sebi.gov.in) — latest edition
- SEBI Circular on Algorithmic Trading Framework for Retail Investors, April 2026
- AMFI Guidelines for Mutual Fund Distributors (amfiindia.com)
- SEBI (Investment Advisers) Regulations, 2013

### Technical Documentation
- Zerodha Kite Connect API: https://kite.trade/docs/connect
- BSE StarMF API Documentation: https://mfapis.in
- LangGraph Documentation: https://langchain-ai.github.io/langgraph
- NSEPython Library: https://github.com/nsepython
- TrueData API: https://truedata.in/docs
- 360dialog WhatsApp Business API: https://docs.360dialog.com

### Competitor Research
- CashRich Dynamic SIP: https://cashrich.in
- 5Paisa Flexi SIP Product Documentation
- Jarvis Invest AI Portfolio Management: https://jarvisinvest.com
- ET Money Genius Advisory Feature

---

> **Document Version:** 1.0
> **Author:** Mahesh
> **Program:** AI-Native Learning Program — Week 1 Deliverable
> **Date:** August 2026
> **Status:** Research Complete — Ready for Design & Development Phase

---
