# Monaco Salle Blanche Lab - Roulette Strategist's Comprehensive Brief

**Document Version:** 1.0  
**Date:** January 9, 2026  
**Purpose:** Complete guide for simulating, testing, and optimizing roulette strategies for real-world Monaco casino play

---

## Table of Contents
1. [System Overview](#system-overview)
2. [How the Simulator Works](#how-the-simulator-works)
3. [Configuration Settings](#configuration-settings)
4. [Progression Systems](#progression-systems)
5. [Spice System (Advanced Sector Betting)](#spice-system)
6. [Results Interpretation](#results-interpretation)
7. [Best Practices for Strategy Development](#best-practices)
8. [Quick Start Guide](#quick-start-guide)

---

## System Overview

### What Is This System?
The Monaco Salle Blanche Lab is a professional Monte Carlo simulation engine designed to stress-test roulette strategies over long-term timeframes (1-10 years). It simulates hundreds or thousands of parallel "universes" to identify strategies with:
- **High survival rates** (avoiding bankruptcy)
- **Optimal risk/reward ratios**
- **Sustainable profit targets**
- **Real-world applicability** in Monaco casinos

### Core Philosophy
This is **NOT** about finding "winning systems" that beat the house edge. It's about:
1. **Bankroll management** - Staying solvent over thousands of spins
2. **Risk optimization** - Maximizing profit while minimizing ruin probability
3. **Real-world testing** - Accounting for psychological, financial, and operational constraints
4. **Long-term sustainability** - Strategies that work over years, not days

---

## How the Simulator Works

### Simulation Architecture

#### 1. **Career-Level Simulation**
- **Duration**: 1-10 years
- **Sessions**: 10-100 sessions per year
- **Each Session**: 3-6 "shoes" (hours of play), ~180 spins
- **Parallel Universes**: 10-1000 simultaneous careers
- **Output**: Statistical bands (min, max, median, percentiles)

#### 2. **Session-Level Mechanics**
```
Session Start (Bankroll: €X)
    ↓
For each spin (up to ~180):
    1. Check stop-loss / target profit
    2. Determine bet size (progression system)
    3. Select bet(s) (Red, Black, Odd, Even, etc.)
    4. Evaluate Spice System (optional sector bets)
    5. Spin wheel (European roulette, 0-36)
    6. Resolve main bets + spice bets
    7. Update bankroll, progression state
    8. Check Smart Trailing Stop
    ↓
Session End (Record P/L, exit reason)
```

#### 3. **Physics Engine**
- **Wheel**: European (37 numbers: 0-36, single zero)
- **House Edge**: 2.7% (1/37) on even-money bets
- **Bet Types Supported**:
  - **Even Money**: Red, Black, Odd, Even, 1-18, 19-36
  - **Sector Bets**: Tiers, Orphelins, Voisins, Jeu Zéro (via Spice System)
  - **Complex Strategies**: Salon Privé Lite (5 units), French Main Game (7 units)

#### 4. **Dynamic Tier System**
Your bet size scales with bankroll:
- **Tier 1** (Starting): €5 base bet (€1000+ bankroll)
- **Tier 2** (Growth): €10 base bet (€2000+ bankroll)
- **Tier 3** (Advanced): €20 base bet (€4000+ bankroll)
- **Tier 4+**: Scales exponentially with safety buffer

**Safety Buffer**: Default 25x (need €1250 bankroll for €5 base bet to be "safe")

---

## Configuration Settings

### 1. Simulation Parameters

#### **Universes (Parallel Runs)**
- **Range**: 10-1000
- **Purpose**: Statistical confidence
- **Recommendation**: 
  - Quick test: 50-100
  - Final strategy: 200-500
  - Publication-ready: 500-1000

#### **Years & Sessions**
- **Years**: 1-10 (simulate career lifespan)
- **Sessions/Year**: 10-100 (how often you play)
- **Example**: 20 sessions/year × 10 years = 200 total sessions

### 2. Core Risk Parameters

#### **Stop Loss (units)**
- **Default**: 10 units (€50 for €5 base)
- **Purpose**: Maximum loss per session
- **Strategy**: 
  - Conservative: 10-15 units
  - Balanced: 20-30 units
  - Aggressive: 40-50 units

#### **Target Profit (units)**
- **Default**: 10 units (€50 for €5 base)
- **Purpose**: Lock in wins and end session
- **Strategy**:
  - Quick wins: 5-10 units
  - Session profit: 15-25 units
  - Big score: 30-50 units

#### **Iron Gate (Maximum Losses)**
- **Default**: 3 consecutive losses
- **Purpose**: Enter "virtual mode" (stop betting until win)
- **Effect**: Prevents catastrophic drawdowns
- **Recommendation**: Always keep at 3

### 3. Betting Engine Modes

#### **Standard** (Default)
- Exponential tier scaling (1x → 2x → 4x → 10x → 20x → 40x)
- Best for: Long-term growth with capital protection

#### **Fortress**
- Flat betting at all tiers (no scaling)
- Best for: Maximum safety, slow grind

#### **Titan**
- Aggressive scaling (1x → 2x → 4x)
- Best for: Players with large bankrolls seeking faster growth

#### **Safe Titan**
- Single tier, no scaling
- Best for: Testing progression systems in isolation

### 4. Bet Selection Strategies

#### **Single Bet Mode**
- Choose one: Red, Black, Odd, Even, 1-18, 19-36
- **Example**: Bet on Red every spin

#### **Dual Bet Mode** (Advanced)
- **Primary Bet**: Red, Black, Odd, Even, 1-18, 19-36
- **Secondary Bet**: Same options
- **Example**: Red + Odd (covers 25/37 numbers, ~67.6% coverage)
- **Special Feature**: Some progressions halt second bet during recovery

#### **Complex Strategies**
- **Salon Privé Lite**: 5-unit bet structure (custom pattern)
- **French Main Game**: 7-unit bet structure (custom pattern)

### 5. Shoes Per Session
- **Range**: 1.0 - 6.0 hours
- **Default**: 3.0 (180 spins)
- **Conversion**: 1 shoe = ~60 spins
- **Strategy**: 
  - Quick sessions: 1-2 shoes
  - Standard: 3 shoes
  - Marathon: 5-6 shoes

### 6. Economic Parameters

#### **Contribution per Win**
- **Range**: €0-1000
- **Purpose**: Bankroll injection after winning sessions
- **Real-world**: Salary, dividends, other income

#### **Contribution per Loss**
- **Range**: €0-1000
- **Purpose**: Bankroll support after losses
- **Strategy**: Higher = more bankroll cushion

#### **Luxury Tax**
- **Threshold**: €12,500 (default)
- **Rate**: 25% (default)
- **Purpose**: Simulates taxes on net winnings above threshold

#### **Holiday Bonus**
- **Ceiling**: €5000+ (activates bonus)
- **Purpose**: Simulates annual windfall or profit distribution

#### **Insolvency Floor**
- **Default**: €1000
- **Purpose**: "Game over" threshold
- **Critical**: If bankroll drops below this, career ends

---

## Progression Systems

### Overview
Progression systems determine **how bet sizes change** based on wins/losses. This is the most critical strategic decision.

### 1. **Flat Betting** (Press = 0)
- **Pattern**: Always bet 1 unit
- **Use Case**: Maximum safety, low variance
- **Pros**: Never escalates losses
- **Cons**: Slow profit accumulation

### 2. **Standard Press** (Press = 1)
- **Pattern**: Increase bet by 1 press unit after EACH win
- **Max Depth**: Configurable (1-5 steps)
- **Example**: 
  - Base: €5
  - Win 1: €10 (+€5 press)
  - Win 2: €15 (+€5 press)
  - Lose: Reset to €5

### 3. **Aggressive Press** (Press = 2)
- **Pattern**: Increase bet after 2 consecutive wins
- **Purpose**: Capitalize on winning streaks
- **Strategy**: More conservative than Standard Press

### 4. **La Caroline** (Press = 5)
- **Sequence**: 1 → 1 → 2 → 3 → 4 units
- **Type**: Positive progression (on WINS)
- **Max Bet**: 4 units
- **Reset**: On loss OR reaching level 4
- **Use Case**: Moderate aggression, capped risk

### 5. **Negative Caroline** (Press = 6)
- **Sequence**: 1 → 1 → 2 → 3 → 4 units
- **Type**: Negative progression (on LOSSES)
- **Purpose**: Recovery betting
- **Risk**: Higher than positive Caroline
- **Strategy**: For players comfortable with Martingale-style recovery

### 6. **Negatif 1-2-4-7 Snap-Back** (Press = 7)
- **Sequence**: 1 → 2 → 4 → 7 units (on losses)
- **Special Feature**: Dual-bet halting
  - When one bet enters progression, second bet STOPS
  - Focus all capital on recovery
  - Resume both bets after win or failure
- **Max Bet**: 7 units
- **Best For**: Dual-bet strategies (Red + Odd, Black + Even)
- **Risk**: High, but controlled

### 7. **The Gentle Surgeon** (Press = 8)
- **Sequence**: 1 → 2 → 4 units (on losses)
- **Special Feature**: Dual-bet halting (same as Snap-Back)
- **Max Bet**: 4 units (CAPPED, does not escalate further)
- **Best For**: Conservative recovery
- **Risk**: Low to moderate
- **Strategy**: Safest negative progression

### Choosing a Progression System

| System | Type | Risk | Best For |
|--------|------|------|----------|
| Flat | None | Lowest | Maximum safety |
| Standard Press | Positive | Low | Steady growth |
| Aggressive Press | Positive | Moderate | Streak capitalization |
| La Caroline | Positive | Moderate | Balanced aggression |
| Negative Caroline | Negative | High | Recovery betting |
| Negatif Snap-Back | Negative | High | Dual-bet recovery |
| Gentle Surgeon | Negative | Low-Mod | Conservative recovery |

**Recommendation**: Start with **Gentle Surgeon** or **La Caroline** for testing. These offer good risk/reward balance.

---

## Spice System (Advanced Sector Betting)

### What Are Spices?
**Spices** are optional, profit-triggered sector bets that fire automatically when you're winning. Think of them as "bonus attacks" during favorable runs.

### Why Use Spices?
1. **Amplify profits** during winning sessions
2. **No downside risk** (only fire when already profitable)
3. **Diversification** (sector bets cover different numbers)
4. **Momentum boost** (winning spices increase target profit)

### Three Families

#### **Family A - Light Spices** (Low risk, frequent)
| Spice | Cost | Trigger | Max Uses | Cooldown | Numbers | Best Payout |
|-------|------|---------|----------|----------|---------|-------------|
| **Zéro Léger** | 3u | +15u | 2/session | 5 spins | 7 | 26 (35:1) = 35u |
| **Jeu Zéro** | 4u | +15u | 2/session | 5 spins | 7 | 26 (36:1) = 36u |
| **Zero Crown** | 4u | +15u | 2/session | 5 spins | 7 | 26 (36:1) = 36u |

**Strategy**: Fire early in profit window (+15u to +80u)

#### **Family B - Medium Spices** (Sector bets)
| Spice | Cost | Trigger | Max Uses | Cooldown | Numbers | Best Payout |
|-------|------|---------|----------|----------|---------|-------------|
| **Tiers du Cylindre** | 6u | +25u | 1/session | 8 spins | 12 | Split (17:1) = 17u |
| **Orphelins** | 5u | +25u | 1/session | 8 spins | 8 | 1 (35:1) = 35u |

**Strategy**: Fire during established profit (+25u to +80u)

#### **Family C - Prestige Spices** (VIP high power)
| Spice | Cost | Trigger | Max Uses | Cooldown | Numbers | Best Payout |
|-------|------|---------|----------|----------|---------|-------------|
| **Orphelins en Plein** | 8u | +35u | 1/session | 10 spins | 8 | Straight (35:1) = 35u |
| **Voisins du Zéro** | 9u | +35u | 1/session | 10 spins | 17 | Varies | 24u |

**Strategy**: Fire during strong profit (+35u to +100u)  
**Bonus**: Prestige wins boost target profit by +40u (vs +20u for other families)

### Global Spice Rules
1. **Maximum 3 spices per session** (across all families)
2. **Only 1 spice fires per spin**
3. **Blocked if Caroline at Step 4** (system is stressed)
4. **Blocked if P/L < 0** (only fire when winning)
5. **Cooldown per spice type** (prevents spam)
6. **Profit window enforcement** (min/max P/L required)

### Configuring Spices

Each spice has 6 parameters:
- **Enable**: On/Off switch
- **Trigger**: Minimum profit to activate (units)
- **Max Uses**: Maximum fires per session
- **Cooldown**: Spins between uses
- **Min P/L**: Lower profit window bound (units)
- **Max P/L**: Upper profit window bound (units)

**Example Configuration (Balanced)**:
```
Zéro Léger:
  Enabled: Yes
  Trigger: 15 units
  Max Uses: 2
  Cooldown: 5 spins
  Min P/L: 15 units
  Max P/L: 80 units

Tiers du Cylindre:
  Enabled: Yes
  Trigger: 25 units
  Max Uses: 1
  Cooldown: 8 spins
  Min P/L: 25 units
  Max P/L: 80 units
```

### Spice Strategy Profiles

#### **Conservative** (Beginner)
- Enable: Zéro Léger only
- Trigger: 20 units (higher)
- Max Uses: 1
- Global Max: 1 per session

#### **Balanced** (Recommended)
- Enable: Zéro Léger + Tiers
- Triggers: 15u / 25u
- Max Uses: 2 / 1
- Global Max: 3 per session

#### **Aggressive** (Advanced)
- Enable: All 7 spices
- Triggers: Lower thresholds
- Max Uses: Maximum allowed
- Global Max: 3 per session

#### **Prestige** (VIP)
- Enable: Family C only (Orphelins Plein, Voisins)
- Triggers: 35 units
- Max Uses: 1 each
- Strategy: Big bankroll, big swings

### Hybrid Mode (Split Table Minimums)
- **Use Case**: Salle Privée with different minimums
- **Example**: €10 chips for Red/Odd, €5 chips for inside bets
- **Effect**: Spice costs are 50% of base bet
- **Enable**: "Hybrid Mode" switch in UI

---

## Results Interpretation

### Career-Level Results

#### **Trajectory Plot**
- **X-axis**: Months (0 to 120 for 10 years)
- **Y-axis**: Bankroll (€)
- **Lines**:
  - **Red solid**: Median trajectory
  - **Red dashed**: Mean trajectory
  - **Dark band**: 25th-75th percentile
  - **Light band**: Min-max range
  - **Red horizontal**: Insolvency floor

**Interpretation**:
- **Upward trend**: Strategy is profitable on average
- **Wide bands**: High variance (risky)
- **Narrow bands**: Low variance (stable)
- **Below insolvency**: Failed universes

#### **Key Statistics**

##### **Average Final GA (Gross Assets)**
- Your expected bankroll after X years
- **Good**: 2-5x starting capital
- **Excellent**: 5-10x starting capital
- **Warning**: < 1.5x starting capital

##### **Survival Rate**
- Percentage of universes above insolvency floor at end
- **Target**: >85% for real-world use
- **Acceptable**: 70-85%
- **Risky**: <70%

##### **Year 1 Failures**
- Universes that went bankrupt in first 12 months
- **Critical**: Should be <10%
- **Warning**: >20% indicates overly aggressive strategy

##### **Average Tax Paid**
- Total taxes paid on profits
- **Indicator**: Only pay taxes if you're winning
- Higher tax = higher profit (good problem to have)

##### **Average Insolvent Months**
- Months spent below insolvency floor
- **Target**: 0-5% of total months
- **Warning**: >10% means too much time in danger zone

##### **Total Input vs Output**
- **Input**: Starting capital + contributions
- **Output**: Final bankroll + taxes + losses
- **Net P/L**: Output - Input
- **ROI**: (Output - Input) / Input × 100%

### Session-Level Analysis

#### **Exit Reasons**
- **TARGET**: Hit profit target (good!)
- **STOP_LOSS**: Hit stop loss (managed risk)
- **TIME_LIMIT**: Ran out of spins (neutral)
- **RATCHET**: Trailing stop triggered (locked profit)
- **SMART_TRAILING**: Adaptive stop triggered (locked profit)

**Distribution to Watch**:
- **Ideal**: 40-50% TARGET exits
- **Balanced**: 30-40% STOP_LOSS, 20-30% TIME_LIMIT
- **Warning**: >60% STOP_LOSS indicates stops are too tight

#### **Peak Progression Levels**
- **Max Caroline**: Highest Caroline level reached
- **Max D'Alembert**: Highest D'Alembert level
- **Interpretation**: 
  - Level 4+ = System was stressed
  - Frequent Level 4 = Strategy too aggressive

### Spice Statistics

#### **Total Spices Fired**
- Average number of spices per career
- **Balanced**: 50-150
- **Aggressive**: 200+
- **Conservative**: <50

#### **Spice Hit Rate**
- Percentage of spice bets that won
- **Expected**: 18-25% (depends on spice type)
- **Reality Check**: Should be close to mathematical probability

#### **Net Spice P/L**
- Total spice payout - total spice cost
- **Interpretation**: Usually break-even or slightly negative
- **Purpose**: Spices are for momentum, not profit
- **Bonus**: Momentum TP gains are the real value

#### **Momentum TP Gains**
- Additional profit captured from target boosts
- **Key Metric**: Shows value of spices beyond direct wins
- **Example**: €640 in momentum gains = spices worked!

#### **Spice Distribution**
- Count of each spice type fired
- **Analysis**: Which spices fired most often?
- **Optimization**: Disable rarely-used spices

---

## Best Practices for Strategy Development

### Phase 1: Quick Testing (2 minutes)
1. **Load default strategy**
2. **Set**: 50 universes, 1 year, 20 sessions/year
3. **Run simulation**
4. **Check**: Survival rate >80%?

### Phase 2: Refinement (15 minutes)
1. **Iterate on variables**:
   - Adjust stop loss (±5 units)
   - Adjust target profit (±5 units)
   - Try different progression systems
2. **Run**: 100 universes, 3 years
3. **Goal**: Find sweet spot with highest ROI + >85% survival

### Phase 3: Long-Term Validation (1 hour)
1. **Final configuration**
2. **Run**: 500 universes, 10 years, 20 sessions/year
3. **Analyze**:
   - Final GA distribution
   - Exit reason breakdown
   - Year-by-year trajectory stability
   - Spice system effectiveness

### Phase 4: Stress Testing
1. **Economic shocks**: Double luxury tax
2. **Bad luck**: Reduce contributions to €0
3. **Variance test**: Increase shoes per session to 6
4. **Goal**: Strategy survives worst-case scenarios

### Strategy Design Principles

#### **1. Survival First**
- A strategy that keeps you in the game is better than one that wins big but fails often
- **Target**: >85% survival rate

#### **2. Manage Variance**
- Use stop losses religiously
- Cap progression systems (prefer Gentle Surgeon over unlimited Martingale)
- Test with worst-case scenarios

#### **3. Bankroll Rules**
- Starting capital should be 50-100x base bet
- Safety buffer: 25x minimum
- Never risk more than 5% of bankroll per session

#### **4. Session Discipline**
- Set time limits (3-4 shoes max)
- Set profit targets (10-25 units)
- Set stop losses (10-30 units)
- **Never** chase losses

#### **5. Progression Discipline**
- Use Iron Gate (3 consecutive losses max)
- Prefer positive progressions (La Caroline) over negative
- If using negative progressions, use capped systems (Gentle Surgeon)

#### **6. Spice System Usage**
- Start conservative (Family A only)
- Only enable spices after testing base strategy
- Spices should be 5-10% of total volume

---

## Quick Start Guide

### Launching the Simulator
```bash
# In terminal
cd /workspaces/MonacoSalleBlancheLab
python main.py
```

Browser opens to: `http://localhost:8080`

### Running Your First Simulation

#### Step 1: Navigate to Roulette Simulator
Click "Roulette Simulator" in the sidebar

#### Step 2: Configure Simulation
- **Universes**: 50
- **Years**: 1
- **Sessions/Year**: 20

#### Step 3: Set Risk Parameters
- **Stop Loss**: 20 units
- **Target Profit**: 15 units
- **Iron Gate**: 3 losses

#### Step 4: Choose Progression
- **Press Logic**: "The Gentle Surgeon (1-2-4)"

#### Step 5: Select Bets
- **Primary Bet**: Red
- **Secondary Bet**: (None for first test)

#### Step 6: Configure Spices (Optional)
- **Enable Zéro Léger**: Yes
- **All others**: No

#### Step 7: Run Simulation
Click **"Run Full Multiverse Sim"**

Wait 10-30 seconds for results...

### Reading Your Results

#### **Look at the Trajectory Plot**
- Is the median line above your starting bankroll?
- Is the 75th percentile line growing steadily?

#### **Check Key Stats**
- **Survival Rate**: Should be >80%
- **Avg Final GA**: Should be >1.5x starting capital
- **Y1 Failures**: Should be <5

#### **Adjust Strategy**
- If survival low: Increase safety, reduce progression depth
- If profit low: Increase target, enable more spices
- If variance high: Use Fortress mode, tighten stops

### Saving Your Strategy
1. **Enter Name**: "My Gentle Strategy v1"
2. **Click "Save Current"**
3. **Strategy saved** to profile.json

### Loading Saved Strategies
1. **Select from dropdown**
2. **Click "Load Selected"**
3. **All settings restored**

---

## Advanced Features

### Smart Trailing Stop
- **Purpose**: Lock in profits dynamically
- **Trigger**: After X spins (default 90)
- **Logic**: If profit drops 20% from peak → exit
- **Use Case**: Capture momentum without fixed targets

**Configuration**:
- **Window Start**: 5-120 spins (default 90, when to activate)
- **Min Profit to Lock**: 20 units (threshold)
- **Trailing Drop %**: 20% (trigger percentage)

**Example**:
```
Spin 100: Profit = €100 (peak)
Spin 120: Profit = €79 (dropped >20%)
→ Session ends, locks in €79 profit
```

### Recovery Session System
- **Purpose**: Automatically play recovery session after loss
- **Trigger**: Any session ending negative
- **Rules**: 
  - Uses same settings as main session
  - Has its own stop loss (default 10 units)
  - Adds "_bis" suffix to session log
- **Use Case**: Give yourself one chance to recover

**Enable**: Recovery Session switch in UI

### Ratchet Mode
- **Purpose**: Progressive profit locking
- **Levels**:
  - +8 units → lock 3 units
  - +12 units → lock 5 units
  - +20 units → lock 10 units
- **Effect**: Guarantees minimum profit if you reach thresholds
- **Modes**:
  - **Standard**: Always active
  - **Gold Grinder**: Disabled for first 2 shoes

### Penalty Box Mode
- **Purpose**: Simulate Monaco casino environment
- **Effect**: After stop loss, replay session at flat bet
- **Use Case**: Replicate real-world "tilting" recovery attempts

---

## Troubleshooting

### "Low survival rate (<50%)"
**Causes**:
- Stop loss too tight
- Progression too aggressive
- Insufficient starting capital

**Solutions**:
- Increase stop loss to 25-30 units
- Use Gentle Surgeon instead of Snap-Back
- Increase starting GA to 100x base bet
- Use Fortress mode

### "Profit too low"
**Causes**:
- Target profit too conservative
- Not using progressions
- Flat betting

**Solutions**:
- Increase target profit to 20-25 units
- Enable La Caroline or Standard Press
- Enable Spice System (Family A + B)

### "High variance (wide bands)"
**Causes**:
- Aggressive progressions
- Too many spices
- Long sessions

**Solutions**:
- Use Gentle Surgeon
- Disable Prestige spices
- Reduce shoes per session to 2-3

### "Year 1 failures >20%"
**Causes**:
- Undercapitalized
- Overly aggressive early tiers

**Solutions**:
- Increase starting GA
- Use Safe Titan mode
- Increase safety buffer to 35x

---

## Real-World Application

### Translating Simulation to Casino Play

#### **Before You Go**
1. Run 500-universe, 10-year simulation
2. Verify >85% survival rate
3. Print session parameters (stop loss, target, base bet)
4. Commit to discipline

#### **At the Table**
1. **Buy-in**: Exactly your safety buffer × base bet
2. **First session**: Follow simulation parameters exactly
3. **Track manually**: Spin count, bet size, P/L
4. **Exit triggers**: Honor stop loss and target religiously

#### **After Session**
1. Log results in session_log.csv
2. Compare to simulation predictions
3. Adjust strategy only after 10+ sessions
4. Never adjust mid-session

### Common Real-World Adjustments

#### **Table Minimums**
- Monaco: €5-€10 minimum inside, €10-€20 outside
- **Solution**: Set base bet to table minimum
- **Hybrid Mode**: Use for split minimums

#### **Table Maximums**
- Monaco: €5,000-€10,000 max
- **Check**: Your max bet never exceeds table max
- **Level 3 Caroline**: 4 units × €10 = €40 (safe)
- **Level 3 Snap-Back**: 7 units × €10 = €70 (safe)

#### **Psychological Factors**
- **Tilt**: Simulation doesn't account for emotions
- **Fatigue**: Stop after 3 hours regardless of P/L
- **Social**: Avoid distractions at table

#### **Operational Constraints**
- **Casino Hours**: Plan session timing
- **Chip Denominations**: Bring correct denominations
- **Cashing Out**: Don't let chips accumulate untracked

---

## Glossary

- **GA (Gross Assets)**: Your current playable bankroll
- **Unit**: Base bet size (e.g., 1 unit = €5)
- **Shoe**: ~60 spins (1 hour of play)
- **Iron Gate**: Auto-stop after X consecutive losses
- **Caroline Level**: Current position in Caroline progression (0-4)
- **Press**: Bet increase after win
- **Spice**: Sector bet fired during profit
- **Ratchet**: Progressive profit lock mechanism
- **Insolvency Floor**: Bankruptcy threshold
- **Survival Rate**: % of universes avoiding bankruptcy
- **Exit Reason**: Why a session ended (TARGET, STOP_LOSS, etc.)
- **Multiverse**: Collection of parallel simulations

---

## Recommended Starting Strategies

### Strategy 1: "The Conservative Grinder"
```
Base Bet: €5
Starting GA: €2500
Progression: Flat Betting (Press = 0)
Bet: Red only
Stop Loss: 20 units (€100)
Target: 15 units (€75)
Spices: None
Shoes: 3
Expected: 90% survival, low profit
```

### Strategy 2: "The Balanced Player" (RECOMMENDED)
```
Base Bet: €10
Starting GA: €5000
Progression: La Caroline (Press = 5)
Bet: Red + Odd (dual bet)
Stop Loss: 25 units (€250)
Target: 20 units (€200)
Spices: Zéro Léger (Trigger: 15u, Max: 2)
Shoes: 3
Iron Gate: 3
Expected: 85% survival, moderate profit
```

### Strategy 3: "The Aggressive Trader"
```
Base Bet: €10
Starting GA: €7500
Progression: Negatif Snap-Back (Press = 7)
Bet: Black + Even (dual bet)
Stop Loss: 40 units (€400)
Target: 30 units (€300)
Spices: Zéro Léger + Tiers (Triggers: 15u/25u)
Shoes: 4
Iron Gate: 3
Smart Trailing: Enabled
Expected: 75% survival, high profit
```

### Strategy 4: "The Spice Master" (ADVANCED)
```
Base Bet: €10
Starting GA: €10,000
Progression: Gentle Surgeon (Press = 8)
Bet: Red + Odd (dual bet)
Stop Loss: 30 units (€300)
Target: 25 units (€250)
Spices: All 7 enabled, balanced triggers
Global Spice Max: 3
Shoes: 3
Iron Gate: 3
Expected: 80% survival, high variance, momentum profits
```

---

## Next Steps

### Immediate Actions
1. **Read**: SPICE_SYSTEM_v5.0.md for deep dive on spices
2. **Read**: GENTLE_SURGEON_GUIDE.md for progression details
3. **Test**: Run "Balanced Player" strategy (50 universes)
4. **Iterate**: Adjust one variable at a time
5. **Validate**: Run final strategy (500 universes, 10 years)

### Medium-Term (Week 1-2)
1. Design 3 custom strategies
2. Compare via multiverse simulation
3. Stress test winner
4. Paper trade (track on paper, don't bet real money)
5. Review results vs simulation predictions

### Long-Term (Month 1-3)
1. Live test with minimum bets
2. Log every session
3. Analyze deviation from simulation
4. Adjust strategy based on 20+ sessions of data
5. Scale up betting after validation

---

## Support & Resources

### Documentation Files
- **SPICE_SYSTEM_v5.0.md**: Complete spice system reference
- **SPICE_QUICK_START.md**: Spice system quick guide
- **GENTLE_SURGEON_GUIDE.md**: Gentle Surgeon progression
- **NEGATIF_SNAPBACK_PROGRESSION.md**: Snap-Back progression
- **README.md**: System overview
- **CSV_DATA_DICTIONARY.md**: Session log format

### Code Files (Reference)
- **engine/roulette_rules.py**: Core roulette physics
- **engine/strategy_rules.py**: Configuration options
- **engine/spice_system.py**: Spice engine logic
- **ui/roulette_sim.py**: Simulator UI and runner

### Testing Your Understanding
Run these test files to see systems in action:
```bash
python test_gentle_surgeon.py
python test_negatif_snapback.py
python test_spice_system.py
python test_full_career.py
```

---

## Final Notes

### Philosophy
This system is designed to help you **avoid ruin** while maximizing entertainment and profit potential. The house edge is real (2.7%) and cannot be beaten long-term. However, **bankroll management** and **disciplined play** can create sustainable, enjoyable casino experiences.

### Reality Check
- Even the best strategies have <90% survival rates over 10 years
- Variance is real—short-term results will differ from simulations
- Discipline is everything—one emotional deviation can ruin a strategy
- The simulator is a **tool**, not a **guarantee**

### Success Criteria
A successful strategy is one where:
1. You stay solvent over years of play
2. You enjoy the process (it's entertainment!)
3. Your average session is break-even or positive
4. You never bet more than you can afford to lose

**Good luck, and may the wheel be in your favor!** 🎰

---

**Document End**  
*For questions or strategy consultation, review your simulation results and iterate methodically.*
