# CSV Data Dictionary - Year 1 Comprehensive Export

## Overview

The Year 1 export now provides comprehensive session-level data for complete strategic analysis. This enhanced format captures not just outcomes, but the **strategic context** that produced those results.

---

## CSV Format

### Baccarat Export
```csv
Month,Session,Result,Total_Bal,Game_Bal,Hands,Volume,Tier,Exit_Reason,Streak_Max
```

### Roulette Export (with Spice Data)
```csv
Month,Session,Result,Total_Bal,Game_Bal,Spins,Volume,Tier,Exit_Reason,Spice_Count,Spice_PL,TP_Boosts,Caroline_Max,DAlembert_Max,Streak_Max
```

---

## Field Definitions

### Common Fields (Both Games)

| Field | Type | Description | Example | Analysis Use |
|-------|------|-------------|---------|--------------|
| **Month** | Integer | Calendar month (1-12) | `1` | Temporal patterns, seasonal analysis |
| **Session** | Integer | Sequential session number within Year 1 | `3` | Session frequency tracking |
| **Result** | Float | Session P/L in euros | `+125.50` | Performance trending |
| **Total_Bal** | Float | Account balance including ecosystem (tax, contrib) | `2125.00` | Solvency tracking |
| **Game_Bal** | Float | Game-only balance (no ecosystem) | `2125.00` | Pure strategy ROI |
| **Volume** | Float | Total € wagered this session | `950.00` | Edge calculation, RTP analysis |
| **Tier** | Integer | Betting tier used (1-10) | `1` | Risk scaling verification |
| **Exit_Reason** | String | Why session ended | `TARGET` | Strategy efficiency |
| **Streak_Max** | Integer | Maximum consecutive wins in session | `4` | Variance/volatility analysis |

### Game-Specific Fields

#### Baccarat Only
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **Hands** | Integer | Total hands played | `180` |

#### Roulette Only
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| **Spins** | Integer | Total spins played | `120` |
| **Spice_Count** | Integer | Number of spice bets fired | `2` |
| **Spice_PL** | Float | Net spice P/L (payout - cost) | `+45.00` |
| **TP_Boosts** | Integer | Number of momentum TP increases | `1` |
| **Caroline_Max** | Integer | Highest Caroline progression level (0-4) | `2` |
| **DAlembert_Max** | Integer | Highest D'Alembert level reached | `3` |

---

## Exit Reason Codes

| Code | Meaning | Strategic Implication |
|------|---------|----------------------|
| **TARGET** | Hit profit target | Strategy working as designed |
| **STOP_LOSS** | Hit stop loss limit | Risk management activated |
| **RATCHET** | Fell below ratchet lock | Profit protection triggered |
| **TIME_LIMIT** | Reached max spins/shoes | Session limit reached naturally |
| **INSOLVENT** | Insufficient bankroll | Can't afford min bet |

---

## Analysis Examples

### Calculate Win Rate
```python
wins = len([r for r in data if r['Result'] > 0])
win_rate = (wins / len(data)) * 100
```

### Calculate Edge
```python
total_result = sum(r['Result'] for r in data)
total_volume = sum(r['Volume'] for r in data)
edge = (total_result / total_volume) * 100
```

### Spice Contribution Analysis (Roulette)
```python
spice_sessions = [r for r in data if r['Spice_Count'] > 0]
spice_roi = sum(r['Spice_PL'] for r in spice_sessions) / len(spice_sessions)
```

### Progression Stress Test
```python
high_stress = [r for r in data if r['Caroline_Max'] >= 3]
stress_rate = (len(high_stress) / len(data)) * 100
```

### Exit Pattern Analysis
```python
from collections import Counter
exit_patterns = Counter(r['Exit_Reason'] for r in data)
# Shows: {'TARGET': 15, 'TIME_LIMIT': 3, 'RATCHET': 2}
```

---

## Strategy Optimization Workflows

### 1. Tier Validation
Check if you're playing at the correct tier for your bankroll:
```python
tier_jumps = [(r['Month'], r['Tier']) for r in data if r['Tier'] > 1]
# If empty and balance is growing: Consider increasing safety factor
```

### 2. Spice Efficiency Matrix (Roulette)
```python
spice_data = [(r['Spice_Count'], r['Spice_PL'], r['Result']) for r in data if r['Spice_Count'] > 0]
avg_spice_roi = sum(s[1] for s in spice_data) / len(spice_data)
sessions_saved_by_spice = len([s for s in spice_data if s[1] > 0 and s[2] > 0])
```

### 3. Streak Correlation
```python
import numpy as np
streaks = [r['Streak_Max'] for r in data]
results = [r['Result'] for r in data]
correlation = np.corrcoef(streaks, results)[0,1]
# High correlation = progression working effectively
```

### 4. Volume Efficiency
```python
# € won per € risked
efficiency = [(r['Result'] / r['Volume']) * 100 for r in data if r['Volume'] > 0]
avg_efficiency = sum(efficiency) / len(efficiency)
# Target: > -2.7% (Monte Carlo house edge)
```

---

## Power Analysis: Multi-Strategy Comparison

Export Year 1 data from multiple strategies, then compare:

```python
import pandas as pd

# Load CSVs
strategy_a = pd.read_csv('strategy_a_y1.csv')
strategy_b = pd.read_csv('strategy_b_y1.csv')

# Compare key metrics
comparison = pd.DataFrame({
    'Strategy_A': [
        strategy_a['Result'].mean(),
        strategy_a['Volume'].sum(),
        (strategy_a['Result'] > 0).sum() / len(strategy_a),
        strategy_a[strategy_a['Exit_Reason'] == 'TARGET'].shape[0]
    ],
    'Strategy_B': [
        strategy_b['Result'].mean(),
        strategy_b['Volume'].sum(),
        (strategy_b['Result'] > 0).sum() / len(strategy_b),
        strategy_b[strategy_b['Exit_Reason'] == 'TARGET'].shape[0]
    ]
}, index=['Avg_Result', 'Total_Volume', 'Win_Rate', 'Target_Hits'])
```

---

## Best Practices

1. **Export After Each Test**: Keep a library of Y1 exports for comparison
2. **Use Session Numbers**: Track actual session frequency vs planned
3. **Monitor Exit Reasons**: Too many STOP_LOSS hits = too aggressive
4. **Track Tier Progression**: Should align with bankroll growth
5. **Analyze Spice ROI**: If negative, reduce spice usage or tighten triggers
6. **Validate Streaks**: Low streak_max with high variance = check progression logic
7. **Compare Game_Bal vs Total_Bal**: Shows ecosystem impact isolation

---

## Import Templates

### Python (Pandas)
```python
import pandas as pd
data = pd.read_csv('year1_export.csv')
```

### Excel
1. Data → From Text/CSV
2. Select file
3. Delimiter: Comma
4. Column types: Automatic

### Google Sheets
1. File → Import
2. Upload → Select file
3. Import location: New sheet
4. Separator: Comma

---

## Sample Output

```csv
Month,Session,Result,Total_Bal,Game_Bal,Spins,Volume,Tier,Exit_Reason,Spice_Count,Spice_PL,TP_Boosts,Caroline_Max,DAlembert_Max,Streak_Max
1,1,125,2125,2125,118,850,1,TARGET,2,45,1,2,0,4
1,2,75,2200,2200,103,720,1,TARGET,1,15,0,1,0,3
1,3,-85,2115,2115,142,980,1,STOP_LOSS,0,0,0,3,0,1
2,4,150,2565,2265,95,680,1,TARGET,3,60,2,1,0,5
```

---

**This comprehensive data format enables professional-grade strategy analysis, optimization, and validation.** 🎯📊
