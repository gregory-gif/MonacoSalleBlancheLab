# Quick Start: Negatif 1-2-4-7 Snap-Back

## What Is It?
A roulette progression that **halts your second bet** when the first enters progression due to a loss.

## How to Use

### Step 1: Launch the App
```bash
python main.py
```

### Step 2: Navigate to Roulette Simulator
Click on "Roulette Simulator" in the menu

### Step 3: Configure
- **Bet Strategy**: Red
- **Bet Strategy 2**: Odd
- **Press Logic**: Select "Negatif 1-2-4-7 Snap-Back"

### Step 4: Set Limits
- **Stop Loss**: 50 units recommended
- **Target Profit**: 30 units recommended

### Step 5: Run
Click "Run Simulation" and watch the magic!

## What You'll See

```
✓ Both bets active normally (€5 + €5)
✓ When one loses → it enters progression
✓ Other bet HALTS until progression completes
✓ On win → both resume at base bet
```

## Progression Sequence
1 → 2 → 4 → 7 units

## Why Use It?
- **Saves Capital**: Only one bet in progression at a time
- **Clear Recovery**: Structured progression path
- **Smart Risk**: Max exposure is 7 units (not 14)

## Quick Test
```bash
python test_snapback_debug.py
```
Watch 20 spins with detailed output!

## Documentation
- [Full Guide](NEGATIF_SNAPBACK_PROGRESSION.md)
- [Implementation Details](SNAPBACK_IMPLEMENTATION_SUMMARY.md)
- [Visual Example](SNAPBACK_VISUAL_EXAMPLE.py)

## Questions?
Read the docs or run the debug test to see it in action!
