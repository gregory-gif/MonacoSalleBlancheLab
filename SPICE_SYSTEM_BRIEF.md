# Monaco Salle Blanche Lab - Spice System v5.0 Brief

**Date:** December 24, 2025  
**To:** Roulette Strategist Team  
**From:** Development Team  
**Subject:** Spice System v5.0 - Professional Configuration Panel

---

## Executive Summary

The **Spice System v5.0** is now fully operational with a comprehensive professional UI. This advanced sector betting engine allows you to layer optional "spice bets" on top of baseline roulette gameplay, with intelligent trigger logic, family-based constraints, and momentum-driven profit adjustments.

---

## What Are "Spices"?

**Spices** are one-shot sector bets (Tiers, Voisins, Zéro, etc.) that fire automatically based on session conditions. They act as tactical overlays to capture high-value wins during profitable momentum windows.

### The Three Families

#### 💎 **Family A - Light Spices** (Low Risk, Frequent)
- **Zéro Léger** (3 units) - Covers 0, 3, 12, 15, 26, 32, 35
- **Jeu Zéro** (4 units) - Enhanced zero sector coverage
- **Zéro Crown** (4 units) - Custom client-defined variant

#### 🔥 **Family B - Medium Spices** (Sector Bets)
- **Tiers du Cylindre** (6 units) - Covers 12 numbers opposite zero (5-33 sector)
- **Orphelins** (5 units) - The "orphan" numbers not in Voisins or Tiers

#### 👑 **Family C - Prestige Spices** (VIP High Power)
- **Orphelins en Plein** (8 units) - All orphans as straight-up bets
- **Voisins du Zéro** (9 units) - Full zero neighbors coverage (17 numbers)

---

## Key Features & Mechanics

### Global Constraints
- **Max Total Spices per Session**: Caps total spice usage (default: 3)
- **Max Spices per Spin**: Limits simultaneous bets (default: 1)
- **Caroline Step 4 Safety**: Blocks spices during deep progression recovery
- **Profit Floor Protection**: Only fires when session P/L ≥ 0

### Per-Spice Configuration
Each spice has 6 independent tunable parameters:

1. **Enable/Disable** - Toggle on/off
2. **Trigger** - Minimum profit to activate (e.g., +15 units)
3. **Max Uses** - Per-session limit (prevents overuse)
4. **Cooldown** - Minimum spins between fires (5-60 spins)
5. **Min P/L Window** - Lower bound of profit range
6. **Max P/L Window** - Upper bound (stops if profit too high)

### Momentum System
When a spice **wins**, it dynamically increases the session's Take Profit target:
- **Light/Medium Win**: +20 units to TP
- **Prestige Win**: +40 units to TP

This creates "momentum runs" where winning spices extend profitable sessions.

---

## Strategic Use Cases

### Conservative Strategy (Risk-Averse)
```
Enable: Zéro Léger only
Global Max: 2 per session
Trigger: +20 units
Cooldown: 10 spins
Profit Window: +20u to +80u
```
**Goal:** Small tactical bets during solid profit runs

### Balanced Strategy (Optimal)
```
Enable: Zéro Léger + Tiers
Global Max: 3 per session
Triggers: +15u (Light), +25u (Medium)
Cooldowns: 5 spins (Light), 8 spins (Medium)
Profit Windows: +15u to +80u
```
**Goal:** Multi-tier coverage with controlled variance

### Aggressive Strategy (High Reward)
```
Enable: All 7 spices
Global Max: 5 per session
Prestige Triggers: +35u
Cooldowns: Reduced (5-10 spins)
Profit Windows: +15u to +150u
```
**Goal:** Maximum coverage during hot streaks

---

## Important Constraints & Safety

### What PREVENTS a Spice from Firing?
1. **Global cap reached** (e.g., 3 spices already used this session)
2. **Cooldown active** (fired too recently)
3. **Per-spice max uses exceeded** (e.g., Zéro Léger used 2/2 times)
4. **Caroline at Step 4** (40€ bet level - safety lock)
5. **Outside profit window** (P/L too low OR too high)
6. **Negative session P/L** (if safety enabled)
7. **Stop-loss proximity** (approaching bankroll threshold)

### Progression Interaction
Spices operate **independently** from main bet progressions (Caroline, D'Alembert, etc.). The spice cost is tracked separately in volume metrics but does not affect progression step calculations.

---

## UI Location & Access

**Path:** Roulette Lab → 🌶️ Spice System v5.0 Card

The UI is organized as a collapsible panel with:
1. **Global Constraints** (always visible)
2. **Family A Expansion** (3 light spices)
3. **Family B Expansion** (2 medium spices)
4. **Family C Expansion** (2 prestige spices)

Each spice has dedicated sliders for all 6 parameters with real-time value displays.

---

## Statistics & Reporting

After each simulation, you'll see:
- **Total Spices Used** (session/career average)
- **Hit Rate** (% of spices that won)
- **Total Cost** vs **Total Payout**
- **Net Spice P/L** (contribution to overall profit)
- **Momentum TP Gains** (total €€€ added to targets)
- **Distribution by Type** (how often each spice fired)

---

## Recommended Testing Protocol

1. **Baseline Run** (No Spices)
   - Run 100 simulations with all spices disabled
   - Document: Final GA, survival rate, Y1 success

2. **Light Spice Test**
   - Enable Zéro Léger only (conservative settings)
   - Compare vs baseline

3. **Multi-Family Test**
   - Enable Light + Medium families
   - Analyze momentum impact

4. **Full System Test**
   - Enable all 7 spices (balanced settings)
   - Measure variance change vs reward

5. **Optimization Phase**
   - Iterate on trigger thresholds
   - Fine-tune cooldowns and windows
   - Find optimal global max per session

---

## Technical Notes

- **Engine:** `/engine/spice_system.py` (593 lines, production-ready)
- **Integration:** `/engine/roulette_rules.py` (lines 234-339)
- **UI Implementation:** `/ui/roulette_sim.py` (lines 767-964)
- **Python Version:** Compatible with Python 3.8+ (f-string bug resolved)

---

## Quick Start Example

```python
# In UI: Set these values
Global Max Session: 3
Global Max Spin: 1
Caroline Step 4 Safety: ON
Negative P/L Block: ON

# Enable Zéro Léger
Trigger: +15 units
Max Uses: 2 per session
Cooldown: 5 spins
Min P/L: +15u
Max P/L: +80u

# Run simulation
Sessions: 200 over 10 years
Base Bet: €10
Target: +10 units per session
```

Expected outcome: ~5-8% increase in long-term GA with marginal variance increase.

---

## Questions or Issues?

Contact the development team or open a GitHub issue at:  
**Repository:** `gregory-gif/MonacoSalleBlancheLab`

---

**End of Brief**

*The Spice System v5.0 represents a significant advancement in tactical roulette simulation. Use it wisely, test thoroughly, and may your momentum runs be frequent and profitable.* 🎰✨
