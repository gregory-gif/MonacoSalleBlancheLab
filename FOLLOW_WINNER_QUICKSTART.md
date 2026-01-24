╔══════════════════════════════════════════════════════════════════════════╗
║                    FOLLOW_WINNER QUICK REFERENCE                         ║
╚══════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────┐
│ WHAT IT DOES                                                             │
├──────────────────────────────────────────────────────────────────────────┤
│ Automatically bets on whichever side (BANKER or PLAYER) won the         │
│ previous hand, EXCEPT when in a progression where it maintains the      │
│ current bet to avoid whipsawing.                                         │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ DECISION LOGIC                                                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   IF first hand OR no history                                           │
│   ├─→ Bet BANKER (default)                                              │
│                                                                          │
│   IF in losing progression (consecutive_losses > 0)                     │
│   ├─→ MAINTAIN current bet (don't switch)                               │
│                                                                          │
│   IF in winning progression (current_press_streak > 0)                  │
│   ├─→ MAINTAIN current bet (ride the streak)                            │
│                                                                          │
│   ELSE (not in progression)                                             │
│   ├─→ FOLLOW last winner (switch to winning side)                       │
│                                                                          │
│   IF last hand was TIE                                                  │
│   └─→ Use last non-TIE outcome                                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ HOW TO USE                                                               │
├──────────────────────────────────────────────────────────────────────────┤
│ 1. Open Baccarat Simulator                                              │
│ 2. Under "Bet Selection", choose FOLLOW_WINNER                          │
│ 3. Configure progressions as usual                                      │
│ 4. Run simulation                                                       │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ EXAMPLE SEQUENCE                                                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Hand  │ Bet     │ Winner  │ Result │ Losses │ Press │ Why?            │
│  ─────┼─────────┼─────────┼────────┼────────┼───────┼─────────────────│
│    1  │ BANKER  │ PLAYER  │ LOSS   │   1    │   0   │ Default         │
│    2  │ PLAYER  │ BANKER  │ LOSS   │   2    │   0   │ Maintain (prog) │
│    3  │ BANKER  │ BANKER  │ WIN    │   0    │   1   │ Maintain (prog) │
│    4  │ BANKER  │ PLAYER  │ LOSS   │   1    │   0   │ Follow winner   │
│    5  │ PLAYER  │ PLAYER  │ WIN    │   0    │   1   │ Maintain (prog) │
│    6  │ PLAYER  │ BANKER  │ LOSS   │   1    │   0   │ Follow winner   │
│    7  │ BANKER  │ BANKER  │ WIN    │   0    │   1   │ Maintain (prog) │
│    8  │ BANKER  │ BANKER  │ WIN    │   0    │   2   │ Follow winner   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ COMPATIBILITY                                                            │
├──────────────────────────────────────────────────────────────────────────┤
│  ✓ Standard Progressions (Flat, Paroli, Titan)                         │
│  ✓ Iron Gate (Virtual Mode)                                            │
│  ✓ Tie Betting                                                          │
│  ✓ Ratchet Locks                                                        │
│  ✓ Smart Trailing Stop                                                  │
│  ✗ Fibonacci Hunter (forces PLAYER only)                                │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ WHEN TO USE                                                              │
├──────────────────────────────────────────────────────────────────────────┤
│  ✓ Tables with hot streaks (BANKER or PLAYER runs)                     │
│  ✓ Want to minimize decision-making                                     │
│  ✓ Prefer adaptive vs. fixed strategy                                   │
│  ✓ Using progressive bet sizing                                         │
│                                                                          │
│  ✗ Strongly prefer one side (use BANKER or PLAYER)                      │
│  ✗ Table has strong chop pattern                                        │
│  ✗ Using Fibonacci Hunter (conflicts)                                   │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ KEY BENEFITS                                                             │
├──────────────────────────────────────────────────────────────────────────┤
│  • Catches momentum shifts automatically                                │
│  • Avoids whipsawing during progressions                                │
│  • No manual bet selection needed                                       │
│  • Works with all existing features                                     │
└──────────────────────────────────────────────────────────────────────────┘

For more details, see:
  • FOLLOW_WINNER_GUIDE.md - Full documentation
  • FOLLOW_WINNER_VISUAL_EXAMPLE.py - Live demonstration
  • test_follow_winner.py - Test cases
