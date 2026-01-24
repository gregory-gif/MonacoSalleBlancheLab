# FOLLOW_WINNER Betting Strategy - Quick Reference

## Overview
The **FOLLOW_WINNER** betting strategy is a dynamic approach that automatically tracks and follows the winning side (BANKER or PLAYER) from the previous hand, with intelligent progression awareness.

## How It Works

### Basic Mode (No Progression)
- **Default Start**: Begins with BANKER on the first hand
- **Follow Winner**: After each hand, switches to bet on whichever side just won
- **After Ties**: Ties are ignored; continues with the last non-tie outcome

### Progression Mode (During Streaks)
The strategy maintains your current bet when you're in a progression to avoid whipsawing:

#### Losing Progression (consecutive_losses > 0)
- **Maintains** the current bet until you win or progression resets
- Prevents switching sides during a recovery attempt

#### Winning Progression (press_streak > 0)  
- **Maintains** the current bet to ride the winning streak
- Continues pressing the same side

## Configuration

### In the Baccarat Simulator UI
1. Go to the Baccarat Simulator
2. Under "Bet Selection", choose **FOLLOW_WINNER**
3. Configure your progression settings as usual

### In Code
```python
from engine.strategy_rules import BetStrategy, StrategyOverrides

overrides = StrategyOverrides(
    bet_strategy=BetStrategy.FOLLOW_WINNER,
    press_trigger_wins=1,  # When to start pressing
    press_depth=3,         # How deep to press
    iron_gate_limit=3      # Loss limit before going virtual
)
```

## Example Sequence

| Hand | Bet     | Winner  | Result | Consecutive Losses | Press Streak | Next Bet Logic |
|------|---------|---------|--------|-------------------|--------------|----------------|
| 1    | BANKER  | PLAYER  | LOSS   | 0 → 1            | 0            | Maintain (in losing prog) |
| 2    | PLAYER  | BANKER  | LOSS   | 1 → 2            | 0            | Maintain (in losing prog) |
| 3    | BANKER  | BANKER  | WIN    | 2 → 0            | 0 → 1        | Follow winner |
| 4    | BANKER  | PLAYER  | LOSS   | 0 → 1            | 1 → 0        | Maintain (in losing prog) |
| 5    | PLAYER  | PLAYER  | WIN    | 1 → 0            | 0 → 1        | Follow winner |
| 6    | PLAYER  | BANKER  | LOSS   | 0 → 1            | 1 → 0        | Maintain (in losing prog) |
| 7    | BANKER  | BANKER  | WIN    | 1 → 0            | 0 → 1        | Follow winner |

## Advantages

1. **Trend Following**: Automatically catches hot streaks on either side
2. **Progression Safety**: Doesn't switch sides during recovery attempts
3. **Adaptability**: Responds to table dynamics without manual intervention
4. **Compatible**: Works with all progression types (Standard, Paroli, Titan, Fibonacci Hunter)

## Use Cases

### Best For:
- Players who want to follow table momentum
- Sessions with streaky table behavior
- Hands-off betting (less decision making)
- Combining with progressive bet sizing

### Not Ideal For:
- Fixed strategy players (prefer BANKER or PLAYER only)
- Tables with alternating chop patterns
- Fibonacci Hunter mode (which forces PLAYER only)

## Technical Details

- **State Tracking**: Uses `state.last_outcome` to remember last non-tie result
- **Progression Detection**: Checks both `consecutive_losses` and `current_press_streak`
- **Default Fallback**: Uses BANKER when no history exists
- **Tie Handling**: Ties are treated as pushes and don't affect the next bet selection

## Compatibility

| Feature | Compatible | Notes |
|---------|-----------|-------|
| Standard Progression | ✓ | Maintains bet during press streaks |
| Paroli | ✓ | Follows winner between cycles |
| Titan | ✓ | Works with all press modes |
| Fibonacci Hunter | ✗ | Fibonacci forces PLAYER only |
| Iron Gate | ✓ | Virtual mode respects last bet |
| Tie Betting | ✓ | Tie bets work independently |
| Ratchet Locks | ✓ | Full compatibility |
| Smart Trailing Stop | ✓ | Full compatibility |

## See Also
- [FOLLOW_WINNER_VISUAL_EXAMPLE.py](FOLLOW_WINNER_VISUAL_EXAMPLE.py) - Interactive demonstration
- [test_follow_winner.py](test_follow_winner.py) - Test cases
- [SPICE_SYSTEM_v5.0.md](SPICE_SYSTEM_v5.0.md) - Overall system documentation
