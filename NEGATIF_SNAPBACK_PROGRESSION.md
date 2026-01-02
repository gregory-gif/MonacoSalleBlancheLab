# Negatif 1-2-4-7 Snap-Back Progression

## Overview
A negative progression system designed for dual-bet roulette strategies with an innovative "halt" mechanism. When one bet enters progression due to a loss, the second bet is automatically halted until the progression completes.

## Progression Sequence
The bet size follows this sequence on consecutive losses:
- **Level 0**: 1 unit (base bet)
- **Level 1**: 2 units
- **Level 2**: 4 units
- **Level 3**: 7 units (maximum)

## Key Features

### 1. Dual-Bet Support
- Works with two simultaneous bets (e.g., Red + Odd, Black + Even)
- Both bets start at base level (1 unit each)

### 2. Progressive Halting Mechanism
When one bet loses and enters progression:
- **Active Bet**: The losing bet enters progression (e.g., Red at 2 units)
- **Halted Bet**: The other bet is suspended (e.g., Odd stops betting)
- **Focus**: All betting power concentrates on recovering the losing bet

### 3. Progression Resolution
The progression completes in two ways:

#### Win Scenario
- The active bet wins at any progression level
- **Result**: Progression resets to level 0
- **Action**: Both bets resume at 1 unit each

#### Fail Scenario
- The active bet loses at level 3 (maximum)
- **Result**: Progression fails and resets
- **Action**: Both bets resume at 1 unit each

### 4. Example Session

```
Spin 1: [Red: €5, Odd: €5]
  → Number: 2 (Black/Even)
  → Red LOSES, Odd WINS (net: €0)
  → Red enters progression at level 1

Spin 2: [Red: €10, Odd: HALTED]
  → Number: 8 (Black/Even)
  → Red LOSES
  → Red advances to level 2

Spin 3: [Red: €20, Odd: HALTED]
  → Number: 14 (Red/Even)
  → Red WINS (€20)
  → Progression completes, both resume

Spin 4: [Red: €5, Odd: €5]
  → Both active again...
```

## Configuration

### In UI (Roulette Simulator)
1. Select two betting strategies (e.g., Red + Odd)
2. Set Press Logic to: **"Negatif 1-2-4-7 Snap-Back"**
3. Configure stop-loss and target profit as desired

### Programmatic Setup
```python
from engine.strategy_rules import StrategyOverrides

overrides = StrategyOverrides(
    press_trigger_wins=7,  # Negatif 1-2-4-7 Snap-Back
    bet_strategy='Red',
    bet_strategy_2='Odd',
    stop_loss_units=50,
    profit_lock_units=30
)
```

## Testing

### Unit Test
```bash
python test_negatif_snapback.py
```
Tests basic progression mechanics with manual scenarios.

### Integration Test
```bash
python test_snapback_integration.py
```
Runs 10 full sessions to verify end-to-end functionality.

### Debug Test
```bash
python test_snapback_debug.py
```
Provides detailed spin-by-spin trace of progression behavior.

## Strategy Benefits

1. **Risk Management**: Concentrates betting power on recovering one bet at a time
2. **Capital Efficiency**: Avoids doubling both bets simultaneously
3. **Clear Recovery Path**: 1→2→4→7 provides structured recovery attempts
4. **Automatic Reset**: Fails gracefully at max level, preventing catastrophic loss
5. **Dual Coverage**: When no progression is active, two bets provide better hit frequency

## Risk Considerations

- **Negative Progression**: Bet sizes increase on losses (inherent risk)
- **Max Drawdown**: Level 3 (7 units) represents maximum single-bet exposure
- **Streak Vulnerability**: Multiple failed progressions can accumulate losses
- **Best Practice**: Set appropriate stop-loss limits and session targets

## Implementation Details

### State Tracking
- `neg_snapback_level`: Current progression level (0-3)
- `bet_in_progression`: Which bet is active (-1 = none, 0 = first, 1 = second)

### Decision Logic
Located in `engine/roulette_rules.py`:
- `get_next_decision()`: Calculates bet size based on progression level
- `resolve_spin_with_individual_tracking()`: Tracks individual bet results
- Progression state updates in `resolve_spin()`

### UI Integration
Located in `ui/roulette_sim.py`:
- Snap-back halt logic in main simulation loop
- Individual bet tracking for dual-bet configurations
- Automatic bet filtering based on progression state

## Version History
- **v1.0** (2026-01-02): Initial implementation with dual-bet halting mechanism
