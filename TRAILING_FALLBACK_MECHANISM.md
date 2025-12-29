# 🔄 Trailing Fallback Mechanism

## Overview
The Trailing Fallback Mechanism is an advanced risk management feature added to Career Mode that provides dynamic protection once you've been promoted to a higher strategy tier. It works alongside the existing standard fallback mechanism to create a two-layer safety net.

## How It Works

### Standard Fallback (Existing)
- **Trigger**: When bankroll drops below X% of the promotion threshold
- **Default**: 80% of promotion threshold
- **Example**: If promoted at €12,000, demote if bankroll falls below €9,600 (80%)

### Trailing Fallback (NEW)
- **Trigger**: Once promoted, tracks your peak bankroll and demotes if you fall X% from that peak
- **Default**: 90% of peak (i.e., 10% drawdown from peak triggers demotion)
- **Activation**: Automatically activates once you exceed the promotion threshold
- **Dynamic**: The "peak" continuously updates as your bankroll grows

## Key Features

### 1. **Dual Protection System**
The system uses **whichever threshold is hit first**:
```
Demote if: current_ga < min(standard_fallback, trailing_fallback)
```

### 2. **Peak Tracking**
- Each strategy leg maintains its own peak tracker
- Peak updates automatically whenever you reach a new high
- Resets when you're demoted back to previous strategy

### 3. **Visual Feedback**
When a demotion occurs, the log shows which mechanism triggered:
- `STANDARD DEMOTED`: Standard fallback threshold was hit
- `🔄 TRAILING DEMOTED`: Trailing fallback from peak was hit

## Example Scenario

**Setup:**
- Strategy A → Strategy B at €10,000 target
- Promotion Buffer: 120% (promote at €12,000)
- Standard Fallback: 80% (demote below €9,600)
- Trailing Fallback: 90% (demote on 10% drawdown from peak)

**Timeline:**

| Month | Bankroll | Peak | Trailing Threshold | Standard Threshold | Status |
|-------|----------|------|-------------------|-------------------|--------|
| 1 | €12,000 | €12,000 | €10,800 (90%) | €9,600 | ✅ PROMOTED to Strategy B |
| 5 | €15,000 | €15,000 | €13,500 (90%) | €9,600 | ✅ Peak updated |
| 8 | €18,000 | €18,000 | €16,200 (90%) | €9,600 | ✅ Peak updated |
| 10 | €16,500 | €18,000 | €16,200 (90%) | €9,600 | ✅ Still safe (above €16,200) |
| 12 | €16,000 | €18,000 | €16,200 (90%) | €9,600 | 🔄 **TRAILING DEMOTED** (fell below €16,200) |

**Without Trailing Fallback**, you would stay in Strategy B until falling all the way to €9,600, risking a much larger drawdown.

**With Trailing Fallback**, you're demoted at €16,000, preserving much more of your gains.

## Configuration

### UI Controls (Career Mode)

**🔄 FALLBACK MECHANISM**
- **Fallback Threshold**: 60-95% (default: 80%)
  - Standard protection below promotion threshold

**🔄 TRAILING FALLBACK MECHANISM** (NEW)
- **Trailing Fallback**: 85-98% (default: 90%)
  - Percentage of peak that triggers demotion
  - Lower = more conservative (earlier exit on drawdown)
  - Higher = more aggressive (larger drawdown allowed)

### Recommended Settings

**Conservative** (Protect Gains):
- Trailing Fallback: 92-95%
- Accept smaller drawdowns, preserve more profits

**Balanced** (Default):
- Trailing Fallback: 90%
- 10% drawdown tolerance from peak

**Aggressive** (Maximize Run):
- Trailing Fallback: 85-88%
- Allow larger drawdowns, stay in higher tier longer

## Technical Implementation

### Core Logic
```python
# Track peak for each strategy leg
if current_ga > trailing_peak[current_leg_idx]:
    trailing_peak[current_leg_idx] = current_ga
    trailing_active[current_leg_idx] = True

# Calculate both thresholds
fallback_threshold = promotion_thresholds[current_leg_idx] * fallback_threshold_pct
trailing_threshold = trailing_peak[current_leg_idx] * trailing_fallback_pct

# Demote if either threshold is breached
if current_ga < min(fallback_threshold, trailing_threshold):
    # Demote to previous strategy
```

### State Management
- `promotion_thresholds[]`: Stores promotion GA for each leg
- `trailing_peak[]`: Tracks highest GA reached in each leg
- `trailing_active[]`: Flags whether trailing is active for each leg

## Benefits

1. **Lock in Profits**: Automatically protect gains when you hit new peaks
2. **Reduce Risk**: Avoid catastrophic drawdowns in higher-tier strategies
3. **Adaptive**: Adjusts dynamically based on your actual performance
4. **Flexible**: Configurable threshold allows customization for risk tolerance
5. **Smart Recovery**: Returns to lower tier to rebuild before re-promotion

## CSV Export

The trailing fallback setting is now included in career simulation exports:
```
Fallback_Threshold,80
Promotion_Buffer,120
Trailing_Fallback,90
```

## Use Cases

### When to Use Higher Values (95-98%)
- Very confident in strategy performance
- Want to maximize time in higher tiers
- Can handle larger drawdowns psychologically
- Strong recovery mechanics in place

### When to Use Lower Values (85-88%)
- Conservative risk management
- Testing new strategy sequences
- Smaller bankroll relative to tier requirements
- Want to preserve capital over growth

## Integration with Other Systems

The trailing fallback works seamlessly with:
- ✅ Doctrine Engine (state transitions still managed independently)
- ✅ Ecosystem (tax/contributions still applied)
- ✅ Multi-leg careers (each leg tracks independently)
- ✅ Both Baccarat and Roulette game modes

## Notes

- Trailing fallback only activates AFTER promotion
- Standard fallback always remains active as base protection
- Both mechanisms can coexist - most protective one triggers first
- Reset occurs when demoted (fresh start in previous tier)
- Peak tracking is leg-specific (doesn't carry over between strategies)
