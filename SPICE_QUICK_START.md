# 🚀 Spice System v5.0 - Quick Start Guide

## What is the Spice System?

The **Spice System v5.0** adds optional, profit-triggered sector bets to your Monaco roulette sessions. Think of spices as "bonus plays" that automatically fire when you're winning, giving you a chance to amplify profits during favorable runs.

---

## ⚡ Quick Setup (2 Minutes)

### 1. Understanding the Basics

**3 Families of Spices:**
- **Light (A):** Small, frequent bets. Trigger at +15u profit. (Zéro Léger, Jeu Zéro, Zero Crown)
- **Medium (B):** Larger sector bets. Trigger at +25u profit. (Tiers, Orphelins)
- **Prestige (C):** VIP high-power bets. Trigger at +35u profit. (Orphelins Plein, Voisins)

**Key Rules:**
- Maximum 3 spices per session
- Only 1 spice fires per spin
- Blocked when Caroline is stressed (Step 4)
- Each spice has a cooldown period

### 2. Running Your First Simulation

The spice system is already integrated. Just configure and run:

```python
# In the UI, enable spices via switches
# OR programmatically:

from engine.strategy_rules import StrategyOverrides

overrides = StrategyOverrides(
    # Enable Zéro Léger (Light spice)
    spice_zero_leger_enabled=True,
    spice_zero_leger_trigger=15,      # Fire when P/L >= +15u
    spice_zero_leger_max=2,           # Max 2 uses per session
    spice_zero_leger_cooldown=5,      # 5 spins between uses
    
    # Enable Tiers (Medium spice)
    spice_tiers_enabled=True,
    spice_tiers_trigger=25,
    spice_tiers_max=1,
    spice_tiers_cooldown=8,
    
    # ... other settings
)

# Run simulation as normal - spices fire automatically!
```

### 3. Checking Results

After your simulation, check the stats:

```
=== SPICE BET STATS v5.0 ===
Total Spices Fired: 127.4 (avg per career)
Spice Wins: 48.2 | Losses: 79.2
Spice Hit Rate: 37.8%
Total Spice Cost: €1,850
Total Spice Payout: €2,100
Net Spice P/L: +€250
Momentum TP Gains: €640

Spice Distribution:
  ZERO_LEGER: 85.3
  TIERS: 42.1
```

---

## 🎯 Common Configurations

### Conservative (Beginner)
```python
# Only enable Light spices, high trigger
spice_zero_leger_enabled=True
spice_zero_leger_trigger=20    # Higher trigger = safer
spice_zero_leger_max=1         # Only 1 use
spice_global_max_per_session=1 # Total limit
```

### Balanced (Recommended)
```python
# Default v5.0 configuration
spice_zero_leger_enabled=True
spice_zero_leger_trigger=15
spice_zero_leger_max=2

spice_tiers_enabled=True
spice_tiers_trigger=25
spice_tiers_max=1

spice_global_max_per_session=3
```

### Aggressive (Advanced)
```python
# Enable all families, lower triggers
spice_zero_leger_enabled=True
spice_zero_leger_trigger=10    # Lower trigger = more fires

spice_tiers_enabled=True
spice_tiers_trigger=20

spice_voisins_enabled=True
spice_voisins_trigger=30       # Enable Prestige

spice_global_max_per_session=5 # Higher limit
```

---

## 📊 Understanding the Results

### Hit Rate
**What it means:** Percentage of spice bets that won.

- **< 30%:** Low hit rate (expected for roulette)
- **30-40%:** Average performance
- **> 40%:** Lucky session variance

### Net Spice P/L
**What it means:** Total profit/loss from all spice bets.

- **Positive:** Spices contributed to profit
- **Zero:** Breakeven
- **Negative:** Spices cost more than they returned

### Momentum TP Gains
**What it means:** How much your Target Profit increased due to spice wins.

- Higher = More aggressive sessions
- Each Light/Medium win: +€200 (20u × €10)
- Each Prestige win: +€400 (40u × €10)

---

## 🔧 Tuning for Your Style

### Problem: Spices never fire
**Fix:** Lower triggers or widen profit windows
```python
spice_zero_leger_trigger=10    # Was 15
spice_zero_leger_max_pl=100    # Was 80
```

### Problem: Too many spices, eating into profit
**Fix:** Raise triggers or tighten global cap
```python
spice_zero_leger_trigger=20    # Was 15
spice_global_max_per_session=2 # Was 3
```

### Problem: Want bigger wins
**Fix:** Enable Prestige spices
```python
spice_voisins_enabled=True
spice_voisins_trigger=35
spice_voisins_max=1
```

---

## 🎓 Pro Tips

1. **Start Conservative:** Enable only 1-2 Light spices first
2. **Monitor Hit Rate:** If < 25%, consider disabling spices
3. **Use Momentum:** Prestige spices are best when you want to "chase the win"
4. **Safety First:** Keep `spice_disable_if_caroline_step4=True`
5. **Experiment:** Try different trigger levels (10-30u range)

---

## 🧪 Testing Your Configuration

Run the test suite to validate:

```bash
cd /workspaces/MonacoSalleBlancheLab
python test_spice_system.py
```

All tests should pass (✓).

---

## 📚 More Resources

- **Full Documentation:** `SPICE_SYSTEM_v5.0.md`
- **Visual Architecture:** `SPICE_ARCHITECTURE_VISUAL.md`
- **Implementation Details:** `IMPLEMENTATION_SUMMARY.md`

---

## 🆘 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Spices not firing | Check P/L is above trigger, Caroline not at Step 4 |
| Statistics showing zero | Ensure spices enabled and session completed |
| Errors on simulation | Verify all spice configs populated (or use defaults) |
| Hit rate too low | This is normal for roulette (house edge ~2.7%) |

---

## 💡 Example: First Session Setup

```python
from engine.strategy_rules import StrategyOverrides
from ui.roulette_sim import RouletteWorker

# Simple setup: Just Zéro Léger
overrides = StrategyOverrides(
    # Main settings
    stop_loss_units=10,
    profit_lock_units=20,
    press_trigger_wins=5,  # La Caroline
    
    # Enable one spice
    spice_zero_leger_enabled=True,
    spice_zero_leger_trigger=15,
    spice_zero_leger_max=2,
    spice_zero_leger_cooldown=5,
    
    # Keep defaults for others (disabled)
)

# Run a single session
pnl, volume, tier, spins, spice_stats = RouletteWorker.run_session(
    current_ga=5000,
    overrides=overrides,
    tier_map=...,  # your tier map
    use_ratchet=False,
    penalty_mode=False,
    active_level=1,
    mode='Standard',
    base_bet=10.0
)

print(f"Session P/L: €{pnl:.2f}")
print(f"Spices used: {spice_stats['total_spices_used']}")
print(f"Net spice contribution: €{spice_stats['net_spice_pl']:.2f}")
```

---

## 🎉 You're Ready!

The Spice System is now active in your simulator. Start with conservative settings and adjust based on results.

**Remember:** Spices are **optional enhancements**. Your base Crossfire strategy still runs independently. Spices just add extra firepower when you're winning!

---

*Happy spinning! 🎰*

**Monaco Salle Blanche Lab - Spice System v5.0**  
© 2025
