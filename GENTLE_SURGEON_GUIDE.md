# The Gentle Surgeon (1-2-4) - Quick Reference

## Overview
**The Gentle Surgeon** is a conservative negative progression system designed for controlled recovery with minimal risk exposure. It uses a **1-2-4 betting sequence** on losses with immediate reset on wins.

## Key Characteristics

- **Type**: Negative Progression
- **Sequence**: 1 → 2 → 4 units
- **Maximum Bet**: 4 units (caps after 2 consecutive losses)
- **Reset**: Immediate on any win
- **Risk Level**: Low to Moderate

## How It Works

### Progression Rules
1. **Start**: Bet 1 unit
2. **On Loss**: Advance to next level (1→2→4)
3. **On Win**: Reset to 1 unit
4. **At Cap**: Stay at 4 units until win

### Betting Sequence Example
```
Spin 1: 1u (Loss)  → Total: -1u  → Next: 2u
Spin 2: 2u (Loss)  → Total: -3u  → Next: 4u
Spin 3: 4u (Loss)  → Total: -7u  → Next: 4u (capped)
Spin 4: 4u (Win)   → Total: -3u  → Next: 1u (reset)
```

## Using in Monaco Salle Blanche Lab

### In the UI
1. Launch the application: `python main.py`
2. Navigate to **Roulette Simulator**
3. Configure your session:
   - Set your base bet (e.g., €10)
   - Choose your bet type (Red, Black, etc.)
   - **Press Logic**: Select **"The Gentle Surgeon (1-2-4)"**
4. Run simulation

### In Code
```python
from engine.strategy_rules import StrategyOverrides

overrides = StrategyOverrides(
    press_trigger_wins=8,  # The Gentle Surgeon
    stop_loss_units=20,    # Recommended
    profit_lock_units=15,   # Recommended
)
```

## Dual-Bet Mode

When playing two bets simultaneously (e.g., Red + Even), The Gentle Surgeon uses **individual bet tracking**:

- Each bet progresses independently
- If one bet enters progression, the other **halts**
- Once the progression bet wins or maxes out, both bets resume
- This prevents double exposure during recovery

### Example: Dual-Bet with Halting
```
Bet A (Red) | Bet B (Even)
------------+-------------
1u (Loss)   | 1u (Win)    → Bet A enters progression
2u (only)   | HALT        → Only Bet A plays
2u (Win)    | RESUME      → Both back to normal
1u          | 1u          → Flat betting resumes
```

## Comparison to Other Progressions

| Progression | Sequence | Levels | Max Bet | Risk |
|-------------|----------|--------|---------|------|
| **Gentle Surgeon** | 1-2-4 | 3 | 4u | Low |
| Negative Caroline | 1-1-2-3-4 | 5 | 4u | Low |
| Negatif Snap-Back | 1-2-4-7 | 4 | 7u | Moderate |
| D'Alembert | 1-2-3-4-5 | ∞ | 5u* | Moderate |

*Capped at 5u in this system

## Risk Management Tips

1. **Recommended Bankroll**: 40+ units minimum
2. **Stop Loss**: Set at -20 to -30 units
3. **Profit Target**: Set at +15 to +20 units
4. **Session Length**: 100-200 spins maximum
5. **Iron Gate**: Keep enabled (stops progression after 3 losses)

## When to Use

**Best For:**
- Conservative players seeking controlled recovery
- Limited bankrolls (starts gentle)
- Shorter sessions
- Players uncomfortable with aggressive progressions

**Avoid When:**
- You need aggressive recovery potential
- Expecting long losing streaks
- Playing high minimum tables (limits cap effectiveness)

## Testing

Run the test suite to verify functionality:
```bash
python test_gentle_surgeon.py
```

View visual examples:
```bash
python GENTLE_SURGEON_VISUAL_EXAMPLE.py
```

## Mathematical Profile

### Maximum Drawdown (3 consecutive losses)
- Total loss: 1 + 2 + 4 = **7 units**
- Recovery on win: 4 units
- Net after recovery: -3 units

### Break-Even Requirements
After hitting max progression (7u loss):
- Need **2 wins** at capped level (4u each) = +8u
- Result: +1u profit

### Win Rate Tolerance
With 50/50 odds (adjusted for 0):
- System breaks even around **48% win rate**
- Profitable at standard roulette win rates (48.6% for even money)

## History & Philosophy

The name "Gentle Surgeon" reflects the system's approach:
- **Gentle**: Conservative escalation, quick cap
- **Surgeon**: Precise, calculated recovery
- Designed for players who want **controlled aggression** without reckless betting

Unlike aggressive martingales, The Gentle Surgeon prioritizes:
1. Bankroll preservation
2. Quick recovery potential
3. Limited downside exposure
4. Psychological comfort

---

**Version**: 1.0  
**Added**: January 2026  
**System ID**: Press Logic #8
