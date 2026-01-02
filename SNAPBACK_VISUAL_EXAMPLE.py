"""
Visual Example: Negatif 1-2-4-7 Snap-Back in Action
====================================================

Scenario: Betting Red + Odd with €5 base unit

┌─────────────────────────────────────────────────────────────────┐
│ SPIN 1 - Both Bets Active                                        │
├─────────────────────────────────────────────────────────────────┤
│ Bets: Red €5 | Odd €5                                           │
│ Number: 17 (Black/Odd)                                          │
│ Result: Red LOSES | Odd WINS                                    │
│ P&L: -€5 + €5 = €0                                              │
│ → Red enters PROGRESSION at Level 1                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ SPIN 2 - Red in Progression, Odd HALTED                         │
├─────────────────────────────────────────────────────────────────┤
│ Bets: Red €10 | Odd €0 (HALTED)                                │
│ Number: 8 (Black/Even)                                          │
│ Result: Red LOSES                                               │
│ P&L: -€10                                                        │
│ → Red advances to Level 2                                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ SPIN 3 - Red Still in Progression                               │
├─────────────────────────────────────────────────────────────────┤
│ Bets: Red €20 | Odd €0 (HALTED)                                │
│ Number: 14 (Red/Even)                                           │
│ Result: Red WINS                                                │
│ P&L: +€20                                                        │
│ → Progression COMPLETES - Reset to both bets                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ SPIN 4 - Both Bets Active Again                                 │
├─────────────────────────────────────────────────────────────────┤
│ Bets: Red €5 | Odd €5                                           │
│ Number: 32 (Red/Even)                                           │
│ Result: Red WINS | Odd LOSES                                    │
│ P&L: +€5 - €5 = €0                                              │
│ → Odd enters PROGRESSION at Level 1                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ SPIN 5 - Odd in Progression, Red HALTED                         │
├─────────────────────────────────────────────────────────────────┤
│ Bets: Red €0 (HALTED) | Odd €10                                │
│ Number: 1 (Red/Odd)                                             │
│ Result: Odd WINS                                                │
│ P&L: +€10                                                        │
│ → Progression COMPLETES - Reset to both bets                    │
└─────────────────────────────────────────────────────────────────┘


Key Observations:
═════════════════

1. HALTING MECHANISM:
   When one bet enters progression, the other stops betting.
   This prevents compounding losses on both bets simultaneously.

2. INDEPENDENT RECOVERY:
   Each bet can enter its own progression cycle.
   Red's progression is separate from Odd's progression.

3. PROGRESSION SEQUENCE:
   Level 0: 1 unit (€5)
   Level 1: 2 units (€10)
   Level 2: 4 units (€20)
   Level 3: 7 units (€35)

4. SNAP-BACK BEHAVIOR:
   On Win: Immediate reset → both bets at 1 unit
   On Fail (level 3 loss): Reset → both bets at 1 unit

5. CAPITAL EFFICIENCY:
   Maximum single-spin exposure: 7 units (€35 if base is €5)
   Compare to doubling both: 14 units (€70 if base is €5)


Worst-Case Scenario (Max Level Failure):
═════════════════════════════════════════

Spin 1: Both active [€5 + €5]    → Red loses, Odd wins (€0 net)
Spin 2: Red only [€10]            → Red loses (-€10)
Spin 3: Red only [€20]            → Red loses (-€20)
Spin 4: Red only [€35]            → Red loses (-€35)
────────────────────────────────────────────────────────────
Total loss: €65 (from Red's progression)
Reset: Back to both bets at €5 each


Best-Case Scenario (Level 1 Win):
═══════════════════════════════════

Spin 1: Both active [€5 + €5]    → Red loses, Odd wins (€0 net)
Spin 2: Red only [€10]            → Red wins (+€10)
────────────────────────────────────────────────────────────
Total profit: €10
Reset: Back to both bets at €5 each


Strategy Tips:
══════════════

✓ Use with even-money bets (Red/Black, Odd/Even, High/Low)
✓ Set stop-loss to protect against multiple failed progressions
✓ Target profit should account for progression volatility
✓ Best for sessions with moderate variance expectations
✓ Complementary bets (Red+Odd) provide better coverage

✗ Avoid if bankroll can't sustain max level (35 units total risk)
✗ Not suitable for aggressive sessions (high variance)
✗ Don't combine with other progression systems
"""

print(__doc__)
