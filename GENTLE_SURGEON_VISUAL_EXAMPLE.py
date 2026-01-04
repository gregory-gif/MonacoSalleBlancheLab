#!/usr/bin/env python3
"""
Visual Example: "The Gentle Surgeon" (1-2-4) in Action
A gentle negative progression that caps quickly to protect bankroll.
"""

print("=" * 70)
print("THE GENTLE SURGEON (1-2-4) - VISUAL DEMONSTRATION")
print("=" * 70)
print()
print("A conservative negative progression:")
print("  • On LOSS: bet increases 1 → 2 → 4 (then caps)")
print("  • On WIN: immediately reset to 1 unit")
print("  • Maximum exposure: 4 units")
print()
print("=" * 70)
print()

# Scenario 1: Quick Recovery
print("SCENARIO 1: Quick Recovery After One Loss")
print("-" * 70)
spins = [
    (1, 10, "L", -10, "Lose at base 1u → advance to level 1"),
    (2, 20, "W", 10, "Win at 2u → RESET to level 0"),
    (3, 10, "W", 20, "Flat betting continues"),
]

for spin, bet, result, pnl, note in spins:
    print(f"Spin {spin}: Bet €{bet:>2} → {result} → PnL: €{pnl:>+4} | {note}")

print()

# Scenario 2: Full Progression Cycle
print("SCENARIO 2: Full Progression to Cap (3 losses, then win)")
print("-" * 70)
spins = [
    (1, 10, "L", -10, "Start: 1u → advance to level 1"),
    (2, 20, "L", -30, "Level 1: 2u → advance to level 2"),
    (3, 40, "L", -70, "Level 2: 4u → CAP reached (stays at level 2)"),
    (4, 40, "W", -30, "Still 4u → WIN! RESET to level 0"),
    (5, 10, "W", -20, "Back to base betting"),
]

for spin, bet, result, pnl, note in spins:
    print(f"Spin {spin}: Bet €{bet:>2} → {result} → PnL: €{pnl:>+4} | {note}")

print()

# Scenario 3: Cap Persistence
print("SCENARIO 3: Multiple Losses at Cap")
print("-" * 70)
spins = [
    (1, 10, "L", -10, "1u loss"),
    (2, 20, "L", -30, "2u loss"),
    (3, 40, "L", -70, "4u loss → CAP"),
    (4, 40, "L", -110, "Still 4u (capped)"),
    (5, 40, "L", -150, "Still 4u (capped)"),
    (6, 40, "W", -110, "Win at 4u → RESET"),
    (7, 10, "W", -100, "Back to normal"),
]

for spin, bet, result, pnl, note in spins:
    print(f"Spin {spin}: Bet €{bet:>2} → {result} → PnL: €{pnl:>+4} | {note}")

print()
print("=" * 70)
print("KEY FEATURES:")
print("=" * 70)
print("✓ Gentle escalation: Only 3 levels (1, 2, 4)")
print("✓ Quick cap: Maximum bet reached after just 2 losses")
print("✓ Instant reset: Any win returns to base betting")
print("✓ Bankroll protection: Limited maximum exposure")
print("✓ Ideal for: Conservative players who want recovery")
print("  potential without aggressive betting")
print()
print("COMPARISON TO OTHER PROGRESSIONS:")
print("  • Negative Caroline (1-1-2-3-4): More gradual, 5 levels")
print("  • Negatif Snap-Back (1-2-4-7): More aggressive, higher cap")
print("  • Gentle Surgeon (1-2-4): Balanced, protective, surgical precision")
print()
print("=" * 70)
