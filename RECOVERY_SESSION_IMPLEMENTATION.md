# Recovery Session System - Implementation Summary

## Overview
A new feature has been added to the Roulette Simulator that allows automatic "recovery sessions" (marked as "bis") to be played after any losing session.

## Feature Description

### What It Does
When enabled, if a session ends with a **negative result**, the system automatically plays a second "recovery" session with its own configurable stop loss. This recovery session appears in the results as a "bis" session (e.g., "Session 2 bis").

### Example Scenario
- **Sessions/Year slider set to 12** (1 session per month)
- **Recovery toggle is ON**
- **Recovery stop loss set to 5 units**

If Session 2 ends negative (e.g., -€50), then:
- Session 2 bis is automatically played
- Session 2 bis uses the recovery stop loss (5u instead of regular 10u)
- Results show both sessions in the log

## UI Controls

### Location
The recovery session controls are located in the Roulette Sim interface, below the Doctrine Engine section and above the Tactics section.

### Controls Added
1. **🔄 Recovery Session System Card**
   - **Enable Recovery Sessions Toggle** - Turn the feature on/off
   - **Recovery Stop Loss Slider** - Set the stop loss for recovery sessions (5-50 units, default: 10)
   - Helpful description explaining the feature

### Visual Appearance
- Cyan-colored card with a distinctive "🔄" icon
- Clear toggle switch for enabling/disabling
- Slider with real-time unit display

## Configuration

### Saving/Loading
- Recovery settings are saved with strategy configurations
- Two fields:
  - `recovery_enabled` (boolean)
  - `recovery_stop_loss` (integer, units)

### Default Values
- **Enabled**: False (off by default)
- **Recovery Stop Loss**: 10 units

## Implementation Details

### How It Works
1. After each regular session completes, the system checks:
   - Is recovery enabled?
   - Did the session end negative?
   - Is the player still solvent (GA >= insolvency floor)?

2. If all conditions are met:
   - A new "recovery" session is created
   - It uses identical settings EXCEPT:
     - Stop loss is set to the recovery stop loss value
     - Recovery is disabled for the recovery session (prevents infinite loops)
   
3. The recovery session is tracked and displayed with an `is_recovery: True` flag

### Results Display

#### Flight Recorder (Year 1 Log)
- Recovery sessions are marked with "bis" suffix
- Example: "M2 S3 bis" = Month 2, Session 3 bis (recovery)
- Added a "Session" column to clearly show session numbers

#### Configuration Report
Shows whether recovery sessions are enabled:
```
Recovery Sessions: ENABLED (Stop Loss: 5u)
```
or
```
Recovery Sessions: DISABLED
```

## Code Changes

### Files Modified
1. **`ui/roulette_sim.py`**
   - Added UI controls for recovery session toggle and stop loss
   - Updated save/load functions to include recovery settings
   - Modified `run_full_career()` to implement recovery session logic
   - Updated results display to show "bis" sessions

2. **`engine/strategy_rules.py`**
   - Added `recovery_enabled` and `recovery_stop_loss` fields to `StrategyOverrides` class

### New Test Files
1. **`test_recovery_session.py`** - Basic functionality test
2. **`test_recovery_multiple.py`** - Multiple simulation test showing recovery sessions in action

## Testing

Run the test suite to verify functionality:

```bash
python test_recovery_multiple.py
```

### Expected Output
- Multiple simulations showing mix of normal and recovery sessions
- Recovery sessions clearly marked with "bis"
- Statistics showing recovery session rate

### Sample Test Results
```
Total Normal Sessions: 30
Total Recovery Sessions: 8
Recovery Session Rate: 26.7%
```

## Benefits

1. **Risk Management** - Provides a second chance to recover from a losing session
2. **Flexible Control** - Recovery sessions can have tighter stop losses
3. **Clear Tracking** - Easy to identify which sessions were recovery attempts
4. **Strategic Option** - Players can experiment with different recovery strategies

## Usage Tips

### When to Enable
- Good for aggressive recovery strategies
- Useful when you want to limit the impact of single bad sessions
- Consider enabling with a lower recovery stop loss (e.g., 5u vs 10u regular)

### Recommended Settings
- **Recovery Stop Loss**: 5-7 units (tighter than regular stop loss)
- **Regular Stop Loss**: 10 units
- This creates a "limited recovery attempt" strategy

### Strategy Considerations
- Recovery sessions increase total sessions played per year
- They also increase total volume and casino points earned
- Be aware that recovery sessions can also lose money
- The feature works with all other systems (Doctrine Engine, Spice System, etc.)

## Future Enhancements (Optional)

Potential improvements for the future:
1. Limit number of recovery attempts per session
2. Option to use different betting strategies for recovery
3. Progressive recovery (2nd bis, 3rd bis, etc.)
4. Statistics tracking recovery session success rate
5. Doctrine Engine integration (different recovery rules per doctrine state)

## Notes

- Recovery sessions do NOT trigger additional recovery sessions (prevents infinite loops)
- Recovery sessions respect insolvency rules (won't play if bankroll too low)
- All spice system, progression, and exit rules apply normally to recovery sessions
- Recovery sessions are included in all statistics (spice counts, volume, etc.)
