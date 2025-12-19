# Monaco Salle Blanche Lab ♠️

**Architect:** Gregory
**Status:** Active | **Version:** 2.0 (Life Strategy)
**Tech Stack:** Python 3.11, NiceGUI, Pandas, NumPy, Render

---

### 🎯 Mission

A private high-stakes laboratory designed to reverse-engineer the **SBM Loyalty Program ("Gold Status")**. The lab utilizes advanced Monte-Carlo simulations to optimize "Life Strategy"—balancing maximum status acquisition against strict solvency limits via the **"Iron Gate"** protocol.

The goal is not just "winning hands," but maximizing **Survival Probability** and minimizing the **Real Monthly Cost** of holding Gold status over 10-year timelines.

---

### 🧠 Core Modules

#### 1. The Laboratory (Simulator)

A Monte-Carlo engine capable of running hundreds of parallel "lives" (simulations) to stress-test financial strategies over decades.

* **Supports:** Baccarat & Roulette (European).
* **Logic:** Tests Press Logic (Standard vs. Aggressive), Multipliers, and Betting Patterns (e.g., Red + Even).
* **Stress Testing:** Accounts for Luxury Tax, Inflation, and Insolvency Thresholds.

#### 2. Live Cockpit

Real-time decision assistant for physical play in the Salle Blanche.

* Translates simulation logic into immediate "Bet / No Bet" signals.
* Tracks session progress against the "Unified Ladder."

#### 3. Financial Dashboard

Live tracking of the "Life Strategy" KPIs:

* **GA (Gross Assets):** Current playable bankroll.
* **Grand Total Wealth:** GA + Taxes Paid + SBM Benefits.
* **Net Life PnL:** Total input vs. Total output.

---

### 📊 Key Metrics & Terminology

* **SBM Gold:** The target loyalty status.
* **The Iron Gate (Insolvency):** The hard limit (e.g., €1,000) below which a strategy is considered "failed" or "dead."
* **Real Monthly Cost:** The "true" cost of the strategy per month, factoring in losses, taxes, and initial capital, averaged over 10 years.
* **Survival Rate:** The percentage of simulations that maintain Gold status without hitting the Iron Gate.
* **Active Play Time:** The percentage of months the player remained solvent and active in the casino.

---

### 🛠️ Configuration & Strategy

The lab allows granular control over simulation variables:

* **Modes:** Safe Titan, Aggressive, Balanced.
* **Press Logic:** Configurable multipliers (e.g., x1.5, x2.0) and triggers.
* **Economy:** Adjustable Inflation Rates and Tax Thresholds.

---

### 🚀 Deployment

**Local Development:**

```bash
python3 -m utils.main

```

**Production (Render):**

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker utils.main:app

```
