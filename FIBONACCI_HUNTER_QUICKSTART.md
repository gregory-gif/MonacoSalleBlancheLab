# Fibonacci Hunter - Quick Start Guide

## 🎯 What is Fibonacci Hunter?

A **high-volatility positive progression** strategy for Baccarat that uses the sequence `[1, 1, 2, 3, 5, 8]` with:
- ✅ **WIN** = Move to next step
- ❌ **LOSS** = Hard reset to step 1
- 🎯 **Target** = Win the "killer bet" (8 units) and exit with +20 units profit

---

## ⚡ 30-Second Setup

```python
from engine.strategy_rules import StrategyOverrides

overrides = StrategyOverrides(
    fibonacci_hunter_enabled=True,           # Enable strategy
    fibonacci_hunter_base_unit=100,          # €100 per unit
    fibonacci_hunter_max_step=5,             # Max step (5 = 8 units)
    fibonacci_hunter_action_on_max_win='STOP_SESSION',  # Exit on success
    stop_loss_units=50                       # Safety net
)
```

**That's it!** The strategy is now active.

---

## 📊 How It Works

### The Sequence
```
Step 1: 100 units (1x base)
Step 2: 100 units (1x base)
Step 3: 200 units (2x base)
Step 4: 300 units (3x base)
Step 5: 500 units (5x base)
Step 6: 800 units (8x base) ← "Killer Bet"
```

### Win Scenario
```
Hand 1: 100 → WIN  → +100   | Next: 100
Hand 2: 100 → WIN  → +100   | Next: 200
Hand 3: 200 → WIN  → +200   | Next: 300
Hand 4: 300 → WIN  → +300   | Next: 500
Hand 5: 500 → WIN  → +500   | Next: 800
Hand 6: 800 → WIN  → +800   | 🎯 SESSION EXIT (+2000 total!)
```

### Loss = Reset
```
Hand 1: 100 → WIN  → +100   | Next: 100
Hand 2: 100 → WIN  → +100   | Next: 200
Hand 3: 200 → WIN  → +200   | Next: 300
Hand 4: 300 → LOSS → -300   | Next: 100 (HARD RESET!)
```

---

## 🎮 Two Modes

### Sniper Mode (Default) ⭐ Recommended
```python
fibonacci_hunter_action_on_max_win = 'STOP_SESSION'
```
- Exit immediately after winning killer bet
- Lock in +20 base units profit
- Perfect for controlled sessions

### Marathon Mode (High Variance)
```python
fibonacci_hunter_action_on_max_win = 'RESET_AND_CONTINUE'
```
- Reset to step 1 after killer bet win
- Continue playing for multiple cycles
- Higher risk, higher reward

---

## 💰 Profit Calculator

| Base Unit | Perfect Sequence Profit |
|-----------|------------------------|
| €50 | **€1,000** |
| €100 | **€2,000** |
| €200 | **€4,000** |
| €500 | **€10,000** |

**Formula**: Profit = 20 × Base Unit

---

## 🛡️ Bankroll Requirements

| Level | Bankroll | Example @ €100 Base |
|-------|----------|---------------------|
| **Minimum** | 30× base | €3,000 |
| **Recommended** | 50× base | €5,000 ⭐ |
| **Comfortable** | 100× base | €10,000 |

---

## 🧪 Test Before Use

```bash
# Run comprehensive test suite
python test_fibonacci_hunter.py

# Expected output:
# ✓ Passed: 10/10
# 🎯 ALL TESTS PASSED!
```

```bash
# View visual demonstrations
python FIBONACCI_HUNTER_VISUAL_EXAMPLE.py

# Shows 5 interactive scenarios
```

---

## 📋 Configuration Quick Reference

```python
# BASIC SETUP
fibonacci_hunter_enabled: bool = True       # Turn on/off
fibonacci_hunter_base_unit: int = 100       # €100 per unit

# ADVANCED OPTIONS
fibonacci_hunter_max_step: int = 5          # Don't change (5 = killer bet)
fibonacci_hunter_action_on_max_win: str = 'STOP_SESSION'  # or 'RESET_AND_CONTINUE'

# SAFETY (Recommended)
stop_loss_units: int = 50                   # Stop if down 50 units
iron_gate_limit: int = 999                  # Disable (Fib has own reset)
```

---

## ⚠️ Important Rules

### Always True
- ✅ Bets on **PLAYER side only** (no commission math issues)
- ✅ **Hard reset** on any loss (no gradual retreat)
- ✅ **Ties don't count** (stay at current step)
- ✅ **Stop loss overrides** progression

### Never True
- ❌ Don't manually adjust bets
- ❌ Don't switch to BANKER side
- ❌ Don't modify sequence mid-session
- ❌ Don't play without adequate bankroll

---

## 🎯 When to Use

### ✅ Good For
- Short "sniper" sessions (goal: 1 sequence)
- High variance tolerance
- Adequate bankroll (50+ units)
- Good table conditions

### ❌ Not For
- Risk-averse players
- Limited bankrolls (< 30 units)
- Marathon grinding sessions
- Volatile/choppy tables

---

## 📚 Full Documentation

1. **Complete Guide**: [FIBONACCI_HUNTER_GUIDE.md](FIBONACCI_HUNTER_GUIDE.md)
   - 45+ sections covering everything
   - Mathematical analysis
   - Strategic considerations

2. **Visual Examples**: `python FIBONACCI_HUNTER_VISUAL_EXAMPLE.py`
   - 5 interactive scenarios
   - Real-world demonstrations

3. **Test Suite**: `python test_fibonacci_hunter.py`
   - 10 comprehensive tests
   - All edge cases covered

4. **Implementation Summary**: [FIBONACCI_HUNTER_IMPLEMENTATION_SUMMARY.md](FIBONACCI_HUNTER_IMPLEMENTATION_SUMMARY.md)
   - Technical details
   - Integration notes
   - File changes

---

## 🚨 Emergency Checklist

Before going live:
- [ ] Bankroll ≥ 50 base units?
- [ ] Stop loss configured?
- [ ] Tests passing? (`python test_fibonacci_hunter.py`)
- [ ] Understand hard reset rule?
- [ ] Know when to stop?
- [ ] Comfortable with variance?

---

## 📊 Statistics at a Glance

| Metric | Value |
|--------|-------|
| **Steps in Sequence** | 6 |
| **Max Single Bet** | 8× base |
| **Total Sequence Profit** | 20× base |
| **Perfect Run Probability** | 1.56% @ 50/50 |
| **Average Bet Size** | 3.3× base |
| **Risk Level** | High Variance |

---

## 🏁 Start Now

1. Copy the 30-second setup code above
2. Adjust `fibonacci_hunter_base_unit` to your bankroll
3. Run tests: `python test_fibonacci_hunter.py`
4. Start playing with **Sniper Mode**
5. Exit after winning the killer bet
6. Repeat next session

---

## 🎯 Success Mantra

> **"Six wins. Twenty units. One exit."**

- 6 consecutive wins = complete sequence
- 20 base units profit per cycle
- 1 exit after killer bet (Sniper mode)

---

**Status**: ✅ Production Ready  
**Test Status**: 10/10 Passing  
**Documentation**: Complete  

🎊 **Ready to hunt!**

---

*For questions or issues, consult [FIBONACCI_HUNTER_GUIDE.md](FIBONACCI_HUNTER_GUIDE.md)*
