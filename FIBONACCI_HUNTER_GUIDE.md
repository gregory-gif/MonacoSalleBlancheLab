# Fibonacci Hunter Progression - Implementation Guide

## 🎯 Overview

**Fibonacci Hunter** is a high-volatility positive progression strategy designed for "Sniper" sessions in Baccarat. It uses a controlled Fibonacci-based sequence with strict reset rules and an optional "Take Profit" exit condition.

---

## 📊 Core Algorithm

### Betting Sequence
```
[1, 1, 2, 3, 5, 8] Units
```

### Progression Rules

#### On WIN ✅
- **Advance** to the next step in the sequence
- **Critical**: If you win the final step (8 Units), trigger **SESSION_EXIT** (Sniper Mode)
- **Alternative**: Reset to Step 1 and continue (Marathon Mode)

#### On LOSS ❌
- **Hard Reset** to Step 1 (Index 0)
- **No gradual retreat** - immediate return to base bet
- **No staying at current level** - always reset

#### On TIE 🤝
- **No impact** on progression
- Remain at current step
- Main bet pushes (returned)

---

## ⚙️ Configuration Parameters

### Strategy Settings

```python
# Enable Fibonacci Hunter
fibonacci_hunter_enabled: bool = False

# Base unit (multiplier for sequence)
fibonacci_hunter_base_unit: int = 100

# Max step index (5 = final 8-unit bet)
fibonacci_hunter_max_step: int = 5

# Action after completing sequence
fibonacci_hunter_action_on_max_win: str = 'STOP_SESSION'  
# Options: 'STOP_SESSION' (Sniper) or 'RESET_AND_CONTINUE' (Marathon)
```

### Integration with Existing Systems

```python
# Stop Loss still applies
stop_loss_units: int = 50  # Override progression if hit

# Iron Gate disabled during Fibonacci
iron_gate_limit: int = 999  # Fibonacci has its own reset logic

# Always bets PLAYER side
bet_strategy: any = BetStrategy.PLAYER  # Enforced by strategy
```

---

## 🎮 Usage Example

### Sniper Mode (Default)
**Goal**: Hit the "Killer Bet" (8 units) and exit with maximum profit

```python
from engine.strategy_rules import StrategyOverrides
from engine.baccarat_rules import BaccaratSessionState, BaccaratStrategist
from engine.tier_params import TierConfig

# Configure Fibonacci Hunter
tier = TierConfig(
    level=1, min_ga=0, max_ga=99999,
    base_unit=10, press_unit=10,
    stop_loss=-5000, profit_lock=2000, catastrophic_cap=-10000
)

overrides = StrategyOverrides(
    fibonacci_hunter_enabled=True,
    fibonacci_hunter_base_unit=100,
    fibonacci_hunter_max_step=5,
    fibonacci_hunter_action_on_max_win='STOP_SESSION',
    stop_loss_units=50,
    iron_gate_limit=999
)

state = BaccaratSessionState(tier=tier, overrides=overrides)

# Play session
while state.mode == PlayMode.PLAYING:
    decision = BaccaratStrategist.get_next_decision(state)
    # ... execute bet and get result ...
    BaccaratStrategist.update_state_after_hand(state, won, pnl_change)
```

---

## 📈 Session Flow Examples

### Example 1: Perfect Run (Sniper Success)
```
Bet 1 (100) → WIN  → Next: 100
Bet 2 (100) → WIN  → Next: 200
Bet 3 (200) → WIN  → Next: 300
Bet 4 (300) → WIN  → Next: 500
Bet 5 (500) → WIN  → Next: 800
Bet 6 (800) → WIN  → 🎯 SESSION EXIT (+2000 total)
```

**Total Profit**: +2,000 units (20 base units)

### Example 2: Reset Behavior
```
Bet 1 (100) → WIN  → Next: 100
Bet 2 (100) → WIN  → Next: 200
Bet 3 (200) → WIN  → Next: 300
Bet 4 (300) → LOSS → Next: 100 (HARD RESET)
Bet 1 (100) → LOSS → Next: 100 (Stay at base)
Bet 1 (100) → WIN  → Next: 100
Bet 2 (100) → WIN  → Next: 200
```

### Example 3: Multiple Cycles (Marathon Mode)
```
Cycle 1: Complete sequence → +2000 → Reset to 100
Cycle 2: Complete sequence → +2000 → Reset to 100
Cycle 3: In progress...
```

---

## 🎲 Mathematical Analysis

### Risk/Reward Profile

| Metric | Value |
|--------|-------|
| **Max Exposure (Single Bet)** | 800 units (8x base) |
| **Sequence Total** | 2,000 units (20x base) |
| **Steps to Complete** | 6 consecutive wins |
| **Probability (50/50)** | 1.56% per sequence |
| **Risk per Attempt** | ~100-800 units depending on step |

### Profit Breakdown
```
Step 1: +100 (1u)
Step 2: +100 (1u)
Step 3: +200 (2u)
Step 4: +300 (3u)
Step 5: +500 (5u)
Step 6: +800 (8u)
───────────────────
Total:  +2000 (20u)
```

### Loss Scenarios

**Worst Case (Lose at Step 6)**:
```
+100 +100 +200 +300 +500 -800 = +400 net
Then reset to 100 units
```

**Repeated Losses at Base**:
```
-100 -100 -100... (until stop loss)
```

---

## 🛡️ Safety Features

### 1. Hard Stop Loss
```python
stop_loss_units: int = 50  # 5000 with base_unit=100
```
If P/L drops below stop loss, session ends regardless of progression step.

### 2. Bet Side Control
- **Enforced PLAYER bets** to avoid Banker commission affecting calculations
- Overrides any `bet_strategy` setting

### 3. Session Exit (Sniper Mode)
- Automatic exit after winning killer bet (Step 6)
- Prevents giving back profits in extended play
- Configurable via `fibonacci_hunter_action_on_max_win`

### 4. Tie Handling
- Ties don't affect progression state
- No advance, no reset
- Main bet pushes as per Baccarat rules

---

## 📊 Statistics Tracking

The state object maintains comprehensive statistics:

```python
state.fibonacci_hunter_step_index       # Current step (0-5)
state.fibonacci_hunter_total_cycles     # Completed sequences
state.fibonacci_hunter_max_reached      # Times reached Step 6
```

---

## 🔧 Integration with Existing Systems

### Compatibility Matrix

| Feature | Behavior with Fibonacci Hunter |
|---------|-------------------------------|
| **Press Trigger** | Ignored (Fibonacci has own progression) |
| **Press Depth** | Ignored |
| **Iron Gate** | Can still trigger (sets virtual mode) |
| **Stop Loss** | Active - overrides progression |
| **Profit Target** | Active - checked before betting |
| **Ratchet Lock** | Active - works normally |
| **Tie Betting** | Active - independent system |

### Priority Order
```
1. Session already stopped? → EXIT
2. Virtual mode (Iron Gate)? → OBSERVE
3. Stop loss hit? → EXIT
4. Profit target hit? → EXIT
5. Ratchet lock triggered? → EXIT
6. Iron Gate trigger? → VIRTUAL MODE
7. Fibonacci Hunter enabled? → FIBONACCI BET
8. Standard progression? → STANDARD BET
```

---

## 🧪 Testing & Validation

### Test Suite
Run the comprehensive test suite:
```bash
python test_fibonacci_hunter.py
```

### Test Coverage
- ✅ Basic progression through sequence
- ✅ Hard reset on loss at all levels
- ✅ Multiple reset scenarios
- ✅ Sniper mode exit (Session stop)
- ✅ Marathon mode (Reset and continue)
- ✅ Tie handling
- ✅ Stop loss integration
- ✅ PLAYER side enforcement
- ✅ Statistics tracking
- ✅ Profit calculations

**All 10 tests passing** ✓

---

## 🎯 Strategic Considerations

### When to Use Fibonacci Hunter

**Ideal For:**
- Short "sniper" sessions targeting one big win
- High-variance tolerance players
- Scenarios with good table conditions
- When bankroll can support 50+ base units

**Not Ideal For:**
- Risk-averse players
- Long grinding sessions
- Limited bankrolls (< 30 base units)
- Volatile/choppy tables

### Bankroll Requirements

**Minimum**: 30 base units (e.g., 3,000 with base=100)
**Recommended**: 50 base units (e.g., 5,000 with base=100)
**Comfortable**: 100 base units (e.g., 10,000 with base=100)

### Session Management

**Sniper Mode** (Recommended):
- Set `fibonacci_hunter_action_on_max_win = 'STOP_SESSION'`
- Target: Complete one sequence
- Exit immediately after killer bet win
- Preserve profits

**Marathon Mode** (Aggressive):
- Set `fibonacci_hunter_action_on_max_win = 'RESET_AND_CONTINUE'`
- Target: Multiple sequences
- Higher variance, higher potential
- Risk of giving back profits

---

## 📝 Implementation Notes

### Code Location
- **Configuration**: `engine/strategy_rules.py` (StrategyOverrides)
- **State**: `engine/baccarat_rules.py` (BaccaratSessionState)
- **Logic**: `engine/baccarat_rules.py` (BaccaratStrategist)
- **Tests**: `test_fibonacci_hunter.py`

### Key Functions
```python
# Get next bet decision (includes Fibonacci logic)
BaccaratStrategist.get_next_decision(state)

# Update state after hand result (includes progression logic)
BaccaratStrategist.update_state_after_hand(state, won, pnl_change, was_tie)
```

### State Variables
```python
fibonacci_hunter_step_index: int = 0      # Current position in sequence
fibonacci_hunter_total_cycles: int = 0    # Completed full sequences
fibonacci_hunter_max_reached: int = 0     # Times hit killer bet
```

---

## 🚀 Quick Start

### 1. Enable Strategy
```python
overrides.fibonacci_hunter_enabled = True
```

### 2. Configure Base Unit
```python
overrides.fibonacci_hunter_base_unit = 100  # €100 per unit
```

### 3. Choose Mode
```python
# Sniper (recommended)
overrides.fibonacci_hunter_action_on_max_win = 'STOP_SESSION'

# Marathon (high variance)
overrides.fibonacci_hunter_action_on_max_win = 'RESET_AND_CONTINUE'
```

### 4. Set Safety Limits
```python
overrides.stop_loss_units = 50  # 5000 with base=100
overrides.iron_gate_limit = 999  # Effectively disable
```

### 5. Run Session
```python
state = BaccaratSessionState(tier=tier, overrides=overrides)
# ... game loop ...
```

---

## ⚠️ Important Warnings

1. **High Variance**: This is an aggressive positive progression
2. **Bankroll Required**: Minimum 30 base units
3. **Stop Loss Essential**: Always set appropriate stop loss
4. **Sniper Mode Recommended**: Exit after killer bet win
5. **Not for Grinding**: Designed for quick hits, not marathon sessions
6. **Commission Avoidance**: PLAYER-only bets prevent decimal issues

---

## 📞 Support & Questions

For issues or questions about Fibonacci Hunter:
1. Check test suite results: `python test_fibonacci_hunter.py`
2. Review configuration parameters in this guide
3. Verify integration with existing systems
4. Check state tracking variables for debugging

---

**Status**: ✅ Production Ready  
**Version**: 1.0  
**Last Updated**: January 2026  
**Test Status**: All 10 tests passing  

🎯 **Fibonacci Hunter: Precision. Power. Profit.**
