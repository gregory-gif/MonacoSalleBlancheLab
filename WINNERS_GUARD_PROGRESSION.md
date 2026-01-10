# Winner's Guard Progression (1-1-2-4 with Profit Stop)

## Overview
A profit-protective negative progression system designed for roulette strategies with an intelligent "winner's guard" mechanism. When you're ahead (positive session PnL), the progression **automatically caps at level 2** to protect your profits, preventing you from risking a large bet that could wipe out your gains.

**Rule:** Never use the full progression if you are ahead.

## Progression Sequence

### When Losing (Session PnL ≤ 0)
Full progression sequence on consecutive losses:
- **Level 0**: 1 unit (base bet)
- **Level 1**: 1 unit
- **Level 2**: 2 units
- **Level 3**: 4 units (maximum)

### When Winning (Session PnL > 0)
Protective progression sequence on consecutive losses:
- **Level 0**: 1 unit (base bet)
- **Level 1**: 1 unit
- **Level 2**: 2 units (MAXIMUM - Guard Active!)
- **Level 3**: 🚫 **BLOCKED** - Will not advance beyond level 2

## Key Features

### 1. Profit Protection
- Monitors your session PnL in real-time
- When profitable (PnL > €0), caps progression at level 2 (2 units max)
- Prevents risking large bets when you're ahead

### 2. Full Recovery When Behind
- When losing (PnL ≤ €0), uses full 1-1-2-4 sequence
- Allows more aggressive recovery when you need it
- No restrictions on progression depth

### 3. Dynamic Adaptation
- Guard status updates after every spin based on current PnL
- Seamlessly transitions between protected and full progression modes

### 4. Winner's Guard Example

#### Scenario: You are up +€60

```
Starting Position: Session PnL = +€60 (GUARD ACTIVE)

Spin 1: [Red: €10]
  → Number: 2 (Black)
  → Red LOSES (PnL: +€50)
  → Level 0 → 1

Spin 2: [Red: €10]
  → Number: 4 (Black)
  → Red LOSES (PnL: +€40)
  → Level 1 → 2

Spin 3: [Red: €20]
  → Number: 8 (Black)
  → Red LOSES (PnL: +€20)
  → Level 2 → 2 ⚠️ GUARD STOPS HERE!

Spin 4: [Red: €20]  ← Still betting 2u, NOT 4u!
  → Because you're still up +€20
  → Normal Logic would bet €40 next
  → Winner's Guard: STOP at 2u
  → Protecting your +€20 profit
```

**Why This Matters:**
- If you bet €40 and lose at spin 4, you'd be down -€20
- By stopping at €20, worst case is you break even (+€0)
- You protect your profits while still trying to recover

### 5. Losing Session Example

```
Starting Position: Session PnL = -€30 (NO GUARD)

Spin 1: [Red: €10]
  → Number: 2 (Black)
  → Red LOSES (PnL: -€40)
  → Level 0 → 1

Spin 2: [Red: €10]
  → Number: 4 (Black)
  → Red LOSES (PnL: -€50)
  → Level 1 → 2

Spin 3: [Red: €20]
  → Number: 8 (Black)
  → Red LOSES (PnL: -€70)
  → Level 2 → 3

Spin 4: [Red: €40]  ← Full 4u bet allowed!
  → Because you're down -€70
  → Full progression active
  → More aggressive recovery permitted
```

## Configuration

### In UI (Roulette Simulator)
1. Navigate to Roulette Simulator
2. Set Press Logic to: **"Winner's Guard (1-1-2-4)"**
3. Configure base bet, stop-loss, and target profit as desired

### Programmatic Setup
```python
from engine.strategy_rules import StrategyOverrides

overrides = StrategyOverrides(
    press_trigger_wins=9,  # Winner's Guard
    bet_strategy='Red',
    bet_strategy_2='Odd',  # Optional second bet
    stop_loss_units=50,
    profit_lock_units=30
)
```

## Dual-Bet Support

Like the Negatif Snap-Back and Gentle Surgeon progressions, Winner's Guard supports dual-bet play with progressive halting:

- Works with two simultaneous bets (e.g., Red + Odd, Black + Even)
- Both bets start at base level (1 unit each)
- When one bet loses and enters progression, the other bet is halted
- Focus concentrates on recovering the losing bet
- Both bets resume at 1 unit when progression completes

## Testing

### Unit Test
```bash
python test_winners_guard.py
```
Tests basic progression mechanics including:
- Full 1-1-2-4 progression when losing
- Profit guard activation when ahead
- Cap at level 2 when profitable
- Reset to level 0 on wins

## Strategy Benefits

### ✅ Advantages
1. **Profit Protection**: Prevents risking large bets when ahead
2. **Smart Aggression**: Allows full progression when you need recovery
3. **Psychological Comfort**: Reduces anxiety about "giving back" profits
4. **Risk Management**: Automatic adjustment based on session performance
5. **Dual-Bet Compatible**: Works seamlessly with two-bet strategies

### ⚠️ Considerations
1. **May Miss Big Wins**: Capping at 2u when ahead means smaller recovery potential
2. **Profit Threshold**: Only activates when PnL > €0 (even €0.01 triggers guard)
3. **Session-Based**: Guard resets each session (doesn't carry across sessions)

## Comparison with Other Progressions

| Feature | Winner's Guard | Negatif Snap-Back | Gentle Surgeon |
|---------|---------------|------------------|----------------|
| Sequence (Losing) | 1-1-2-4 | 1-2-4-7 | 1-2-4 |
| Sequence (Winning) | 1-1-2 (capped) | 1-2-4-7 | 1-2-4 |
| Max Bet (Losing) | 4u | 7u | 4u |
| Max Bet (Winning) | 2u | 7u | 4u |
| Profit Protection | ✅ Yes | ❌ No | ❌ No |
| Risk Level | Low-Medium | High | Medium |
| Recovery Speed | Medium | Fast | Medium |
| Best For | Conservative players protecting profits | Aggressive recovery | Balanced play |

## When to Use Winner's Guard

**Ideal Scenarios:**
- You frequently reach profit targets and want to protect gains
- You're risk-averse when ahead
- You play longer sessions where profit protection matters
- You want peace of mind when you're winning

**Not Ideal For:**
- Aggressive players who always want maximum recovery
- Very short sessions where profit protection isn't a concern
- Players who prefer consistent bet sizing regardless of PnL

## Technical Implementation

### State Variables
- `winners_guard_level`: Current progression level (0-3)
- `session_pnl`: Session profit/loss used to determine guard activation
- `bet_in_progression`: For dual-bet halting mechanism

### Logic Flow
1. Check session PnL before calculating bet size
2. If PnL > 0: cap level at 2 (sequence becomes 1-1-2)
3. If PnL ≤ 0: allow full sequence (1-1-2-4)
4. On win: reset to level 0
5. On loss: advance level (respecting the cap)

## See Also
- [Negatif Snap-Back Progression](NEGATIF_SNAPBACK_PROGRESSION.md)
- [Gentle Surgeon Guide](GENTLE_SURGEON_GUIDE.md)
- [Roulette Strategist Brief](ROULETTE_STRATEGIST_BRIEF.md)
