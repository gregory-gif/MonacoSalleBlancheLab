# Monaco Salle Blanche Lab - Spice System v5.0

## Overview

The **Spice System v5.0** is an advanced sector betting framework for European/Monaco roulette that layers optional, profit-dependent one-shot bets on top of the baseline Crossfire gameplay.

### Key Features
- **7 Distinct Spice Types** grouped into 3 families (Light, Medium, Prestige)
- **Fully Configurable** - all triggers, cooldowns, and limits are tunable
- **Global Caps** - maximum 3 spices per session, 1 per spin
- **Profit Window Logic** - spices only fire within specified P/L ranges
- **Caroline Safety Check** - spices disabled when Caroline at Step 4 (stressed)
- **Momentum TP Boost** - target profit increases dynamically on spice wins
- **Comprehensive Statistics** - tracks hit rates, P/L, distribution, momentum gains

---

## Architecture

### Core Components

1. **engine/spice_system.py** - Main spice engine
   - `SpiceEngine` - Main evaluation and execution engine
   - `SpiceRule` - Configuration for individual spice types
   - `GlobalSpiceConfig` - Session-wide constraints
   - `SPICE_PATTERNS` - Bet structure definitions for all 7 spices

2. **engine/roulette_rules.py** - Integration with roulette engine
   - `create_spice_engine_from_overrides()` - Converts UI config to SpiceEngine
   - Updated `RouletteSessionState` with spice engine instance

3. **engine/strategy_rules.py** - Configuration interface
   - All 7 spice types + global settings in `StrategyOverrides`

4. **ui/roulette_sim.py** - UI and simulation
   - `RouletteWorker.run_session()` - Integrated spice evaluation per spin
   - `run_full_career()` - Aggregates spice statistics across careers
   - `calculate_stats()` - Comprehensive spice analytics

---

## Spice Families & Types

### Family A — Light Spices (Low risk, frequent)

| Spice Type | Unit Cost | Trigger | Max Uses | Cooldown | Pattern |
|------------|-----------|---------|----------|----------|---------|
| **Zéro Léger** | 3u | +15u | 2 | 5 spins | 1 straight-up (26) + 3 splits |
| **Jeu Zéro** | 4u | +15u | 2 | 5 spins | Full Jeu Zéro pattern |
| **Zero Crown** | 4u | +15u | 2 | 5 spins | Custom client-defined crown |

**Constraints:**
- Max 2 uses per session (combined across all Family A)
- Cooldown: 5 spins
- Profit window: +15u to +80u

### Family B — Medium Spices (Sector bets)

| Spice Type | Unit Cost | Trigger | Max Uses | Cooldown | Pattern |
|------------|-----------|---------|----------|----------|---------|
| **Tiers du Cylindre** | 6u | +25u | 1 | 8 spins | 6 splits covering 12 numbers |
| **Orphelins** | 5u | +25u | 1 | 8 spins | 1 straight-up + 4 splits |

**Constraints:**
- Max 1 use per session (combined across all Family B)
- Cooldown: 8 spins
- Profit window: +25u to +80u

### Family C — Prestige Spices (High-power VIP bets)

| Spice Type | Unit Cost | Trigger | Max Uses | Cooldown | Pattern |
|------------|-----------|---------|----------|----------|---------|
| **Orphelins en Plein** | 8u | +35u | 1 | 10 spins | 8 straight-ups |
| **Grand Voisins** | 9u | +35u | 1 | 10 spins | Full Voisins du Zéro |

**Constraints:**
- Max 1 use per session (combined across all Family C)
- Cooldown: 10 spins
- Profit window: +35u to +100u
- **Momentum Boost:** +40u to TP on win (vs +20u for other families)

---

## Global Spice Rules

### Mandatory Constraints

1. **Global Session Cap:** Maximum 3 total spices per session (across all families)

2. **Max 1 Spice Per Spin:** Only one spice can fire on any given spin

3. **Caroline Safety Check:** 
   - Spices CANNOT fire if any Caroline line (Red or Odd) is at Step 4 (40€ level)
   - Indicates Crossfire is under stress

4. **Profit Window Logic:**
   ```python
   session_pl_units >= trigger_pl_units
   AND session_pl_units <= max_pl_units
   ```

5. **Stop Loss Lockout:**
   - If `current_bankroll <= (session_start - stop_loss)`, spices disabled for remainder of session

6. **Cooldown System:**
   - Each spice type tracks its own cooldown timer
   - `spins_since_last_use >= cooldown_spins` required to fire

7. **Per-Spice Max Uses:**
   - Enforced per individual spice type
   - Tracked in `SpiceState.used_this_session`

---

## Momentum TP System

### Target Profit Dynamic Adjustment

When a spice **wins**, the session's Target Profit (TP) increases dynamically:

- **Family A & B spices:** `TP += +20 units`
- **Family C (Prestige) spices:** `TP += +40 units`

This creates a "momentum effect" where successful spices push the session target higher, encouraging aggressive play during winning streaks.

**Implementation:**
```python
if spice_won:
    boost = 40u if family == C_PRESTIGE else 20u
    current_tp += boost
    session_overrides.profit_lock_units = int(current_tp / base_bet)
```

---

## Configuration System

### Full Tunability

Every spice parameter is configurable via `StrategyOverrides`:

```python
# Example: Zéro Léger configuration
spice_zero_leger_enabled: bool = False
spice_zero_leger_trigger: int = 15        # P/L threshold to activate
spice_zero_leger_max: int = 2             # Max uses per session
spice_zero_leger_cooldown: int = 5        # Spins between uses
spice_zero_leger_min_pl: int = 15         # Lower profit window bound
spice_zero_leger_max_pl: int = 80         # Upper profit window bound
```

### Global Configuration

```python
spice_global_max_per_session: int = 3     # Total cap (tunable)
spice_global_max_per_spin: int = 1        # Usually 1, tunable for experiments
spice_disable_if_caroline_step4: bool = True  # Safety toggle
spice_disable_if_pl_below_zero: bool = True   # Optional safety
```

---

## Bet Pattern Definitions

### Example: Tiers du Cylindre

```python
SpicePattern(
    pattern_id="TIERS_PATTERN",
    spice_type=SpiceType.TIERS,
    unit_cost=6,
    numbers_covered=[5, 8, 10, 11, 13, 16, 23, 24, 27, 30, 33, 36],
    bet_structure={
        "splits": [[5, 8], [10, 11], [13, 16], [23, 24], [27, 30], [33, 36]]
    },
    payout_map={
        5: 17.0, 8: 17.0, 10: 17.0, 11: 17.0,
        13: 17.0, 16: 17.0, 23: 17.0, 24: 17.0,
        27: 17.0, 30: 17.0, 33: 17.0, 36: 17.0
    }
)
```

All 7 patterns are fully defined in `engine/spice_system.py` with:
- Exact bet structures (straight-ups, splits, corners, trios)
- Payout multipliers for each winning number
- Numbers covered
- Unit costs

---

## Statistics Tracking

### Session-Level Stats

The `SpiceEngine` tracks comprehensive statistics:

```python
{
    "total_spices_used": 3,
    "spice_wins": 2,
    "spice_losses": 1,
    "hit_rate": 0.667,  # 66.7% hit rate
    "total_cost": 150.0,  # €150 total wagered
    "total_payout": 340.0,  # €340 total payout
    "net_spice_pl": 190.0,  # +€190 net from spices
    "momentum_tp_gains": 40.0,  # +€40 to TP from momentum
    "distribution": {
        "ZERO_LEGER": 1,
        "TIERS": 1,
        "VOISINS": 1
    }
}
```

### Career-Level Aggregation

`run_full_career()` aggregates across all sessions:

```python
avg_spice_stats = {
    'total_spices_used': 127.4,  # Avg per career
    'sessions_with_spices': 42.3,
    'hit_rate': 0.38,  # 38% overall hit rate
    'total_cost': 1850.0,
    'total_payout': 2100.0,
    'net_pl': 250.0,  # +€250 avg contribution
    'momentum_tp_gains': 640.0,
    'distribution': {...}
}
```

---

## Usage Examples

### Basic Usage (Default Config)

```python
from engine.spice_system import create_default_engine

# Create engine with v5.0 defaults
spice_engine = create_default_engine()

# Reset for new session
spice_engine.reset_session()

# Each spin:
spice_engine.reset_spin()
fired_spice = spice_engine.evaluate_and_fire_spice(
    session_pl_units=23.5,
    spin_index=45,
    caroline_at_step4=False,
    session_start_bankroll=5000,
    current_bankroll=5235,
    stop_loss=500
)

if fired_spice:
    # Spice fired! Resolve it
    spice_pnl, spice_won = spice_engine.resolve_spice(
        fired_spice, 
        winning_number=27, 
        unit_bet_size=10.0
    )
    
    if spice_won:
        # Apply momentum boost
        new_tp = spice_engine.apply_momentum_tp_boost(
            fired_spice, 
            current_tp=200, 
            unit_size=10
        )

# Get statistics
stats = spice_engine.get_statistics()
```

### Custom Configuration

```python
from engine.spice_system import SpiceEngine, SpiceType, SpiceRule, GlobalSpiceConfig, SpiceFamily

# Custom spice rules
custom_config = {
    SpiceType.TIERS: SpiceRule(
        enabled=True,
        family=SpiceFamily.B_MEDIUM,
        trigger_pl_units=20,  # Lower trigger
        max_uses_per_session=2,  # Allow 2 uses
        cooldown_spins=5,  # Faster cooldown
        min_pl_units=20,
        max_pl_units=100,  # Wider window
        unit_bet_size_eur=10,
        pattern_id="TIERS_PATTERN",
    ),
    # ... define all 7 spices
}

# Custom global config
custom_global = GlobalSpiceConfig(
    max_total_spices_per_session=5,  # Allow 5 total
    max_spices_per_spin=1,
    disable_if_caroline_step4=False,  # Risk mode!
    disable_if_pl_below_zero=False
)

# Create custom engine
engine = SpiceEngine(custom_config, custom_global)
```

### Integration with StrategyOverrides

```python
from engine.roulette_rules import create_spice_engine_from_overrides
from engine.strategy_rules import StrategyOverrides

# Configure via StrategyOverrides
overrides = StrategyOverrides(
    spice_global_max_per_session=3,
    spice_zero_leger_enabled=True,
    spice_zero_leger_trigger=15,
    spice_zero_leger_max=2,
    spice_zero_leger_cooldown=5,
    # ... all other spice configs
)

# Automatically create engine from overrides
engine = create_spice_engine_from_overrides(overrides, unit_size=10.0)
```

---

## Implementation Flow

### Per-Spin Execution

```
1. evaluate_crossfire_bets()
   └─> Determine main bet size (Caroline, D'Alembert, etc.)

2. update_PL()
   └─> Calculate session P/L in units

3. spice_engine.reset_spin()
   └─> Reset per-spin counters

4. IF global_spice_count < max_total AND no spice fired this spin:
   └─> spice_engine.evaluate_and_fire_spice()
       ├─> Check all 7 spices in priority order
       ├─> First eligible spice fires
       └─> Returns SpiceType or None

5. resolve_main_bets()
   └─> Spin wheel, calculate main bet P/L

6. IF spice fired:
   └─> spice_engine.resolve_spice()
       ├─> Calculate spice P/L
       ├─> Update session P/L
       └─> IF spice won:
           └─> apply_momentum_tp_boost()
               └─> TP += 20u (or 40u for Prestige)

7. update_progression_state()
   └─> Caroline, D'Alembert, streak tracking

8. check_session_end_conditions()
   └─> TP hit, SL hit, or spins exhausted
```

---

## Advanced Features

### Preset Management

Store and load complete spice configurations:

```json
{
  "name": "Privée v5.0 (Greg Default)",
  "spiceConfig": {
    "ZERO_LEGER": {
      "enabled": true,
      "trigger_pl_units": 15,
      "max_uses_per_session": 2,
      "cooldown_spins": 5,
      "min_pl_units": 15,
      "max_pl_units": 80
    },
    "TIERS": {...},
    "VOISINS": {...}
  },
  "globalSpiceConfig": {
    "max_total_spices_per_session": 3,
    "max_spices_per_spin": 1,
    "disable_if_caroline_step4": true,
    "disable_if_pl_below_zero": true
  }
}
```

### Experimental Modes

Tune parameters for research:

- **Aggressive Mode:** `max_total_spices_per_session=6`, lower triggers
- **Conservative Mode:** Higher triggers, tighter windows
- **Prestige Only:** Disable A & B families, enable only C
- **Family A Spam:** `max_uses_per_session=10` for Light spices

---

## Performance Considerations

### Efficiency

- **O(1) evaluation** per spice (no loops over all spices per check)
- **Dictionary-based lookups** for pattern resolution
- **Minimal state tracking** - only what's necessary

### Memory

- One `SpiceEngine` instance per session
- `SpiceState` ~1KB per session
- Aggregated stats grow linearly with career length

---

## Future Enhancements

### Potential v6.0 Features

1. **Adaptive Triggers** - ML-based trigger adjustment based on session volatility
2. **Multi-Spice Combos** - Allow 2 spices per spin with combo bonuses
3. **Family Bonuses** - Activate all Family A spices for 1 spin (cost: 11u)
4. **Spice Chains** - Win streak bonuses for consecutive spice wins
5. **Heat Maps** - Visual display of optimal spice fire zones
6. **Backtest Mode** - Replay historical spins with spice optimization

---

## Testing & Validation

### Unit Tests

Run comprehensive tests:

```bash
python -m pytest engine/test_spice_system.py
```

### Validation Checks

1. **Global Cap Enforcement:** Verify max 3 spices per session
2. **Cooldown Logic:** Confirm spices don't fire within cooldown
3. **Caroline Safety:** Test spice lockout at Step 4
4. **Profit Window:** Validate trigger/min/max bounds
5. **Momentum TP:** Verify TP increases correctly on wins
6. **Payout Accuracy:** Test all 7 patterns against known outcomes

---

## Troubleshooting

### Common Issues

**Issue:** Spices never fire
- Check `enabled` flags in config
- Verify profit window ranges (min/max_pl_units)
- Ensure Caroline not at Step 4
- Check global cap not exhausted

**Issue:** Momentum TP not increasing
- Verify `profit_lock_units > 0` in StrategyOverrides
- Check spice actually won (review payout logic)
- Confirm `apply_momentum_tp_boost()` is called

**Issue:** Statistics showing zero
- Ensure `get_statistics()` called after session
- Verify spices actually fired (check logs)
- Confirm `resolve_spice()` called for each fired spice

---

## References

- **Monaco Roulette Rules:** [Casino de Monte-Carlo](https://www.montecarlosbm.com/)
- **Sector Bet Patterns:** Traditional French roulette nomenclature
- **Crossfire System:** Proprietary dual-line Martingale variant

---

## License & Credits

Monaco Salle Blanche Lab - Spice System v5.0  
© 2025 Gregory Gif  
Proprietary & Confidential

---

**For questions or support, contact: gregory@monacosalleblanche.lab**
