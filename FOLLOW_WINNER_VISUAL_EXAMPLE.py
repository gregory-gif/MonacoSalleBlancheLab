"""
═══════════════════════════════════════════════════════════════════════════
                    FOLLOW WINNER BET STRATEGY
                        Visual Example
═══════════════════════════════════════════════════════════════════════════

CONCEPT:
--------
The FOLLOW_WINNER strategy automatically switches your bet to follow the
winning side from the previous hand, EXCEPT when you're in a progression
(either winning or losing streak), where it maintains the current bet.

BASIC BEHAVIOR:
--------------
Hand 1: Bet BANKER (default) → PLAYER wins
Hand 2: Bet PLAYER (follow winner) → BANKER wins
Hand 3: Bet BANKER (follow winner) → BANKER wins
Hand 4: Bet BANKER (follow winner) → PLAYER wins
Hand 5: Bet PLAYER (follow winner) → PLAYER wins
Hand 6: Bet PLAYER (follow winner) → ...

PROGRESSION BEHAVIOR:
--------------------
When you're in a LOSING progression (consecutive losses), the strategy
maintains the current bet until you win or reset:

Hand 1: Bet BANKER → PLAYER wins (Loss 1) ❌
Hand 2: Bet PLAYER (maintain) → BANKER wins (Loss 2) ❌
Hand 3: Bet BANKER (maintain) → BANKER wins (Win!) ✓
Hand 4: Bet BANKER (follow winner) → PLAYER wins (Loss 1) ❌
Hand 5: Bet PLAYER (maintain) → PLAYER wins (Win!) ✓
Hand 6: Bet PLAYER (follow winner) → ...

When you're in a WINNING progression (press streak), it also maintains:

Hand 1: Bet BANKER → BANKER wins (Win, Press Streak = 1) ✓
Hand 2: Bet BANKER (maintain press) → PLAYER wins (Loss) ❌
Hand 3: Bet PLAYER (follow winner) → ...

RATIONALE:
---------
1. NORMAL PLAY: Following winners catches hot streaks
2. DURING PROGRESSION: Maintaining bet avoids whipsawing during recovery
3. TIES: Ignored - continue with last non-tie outcome

═══════════════════════════════════════════════════════════════════════════
"""

from engine.baccarat_rules import BaccaratSessionState, BaccaratStrategist
from engine.strategy_rules import StrategyOverrides, BetStrategy
from engine.tier_params import TierConfig

def demo_follow_winner():
    """Visual demonstration of FOLLOW_WINNER behavior"""
    
    print(__doc__)
    
    tier = TierConfig(
        level=1, min_ga=0, max_ga=10000,
        base_unit=10, press_unit=5,
        stop_loss=-1000, profit_lock=1000,
        catastrophic_cap=-5000
    )
    
    overrides = StrategyOverrides(
        iron_gate_limit=3,
        stop_loss_units=100,
        profit_lock_units=100,
        press_trigger_wins=2,  # Press after 2 wins
        press_depth=3,
        bet_strategy=BetStrategy.FOLLOW_WINNER
    )
    
    state = BaccaratSessionState(tier=tier, overrides=overrides)
    
    print("LIVE DEMONSTRATION")
    print("="*70)
    print(f"{'Hand':<6} {'Our Bet':<12} {'Winner':<10} {'Result':<8} {'P&L':<8} {'Losses':<8} {'Press':<6}")
    print("-"*70)
    
    # Simulated hand outcomes
    hands = [
        ('BANKER', 'PLAYER'),  # We bet BANKER, PLAYER wins (we lose)
        ('PLAYER', 'BANKER'),  # Follow to PLAYER, BANKER wins (we lose) - maintain in progression
        ('BANKER', 'BANKER'),  # Maintain BANKER, BANKER wins (we win!)
        ('BANKER', 'PLAYER'),  # Follow BANKER, PLAYER wins (we lose)
        ('PLAYER', 'PLAYER'),  # Maintain PLAYER, PLAYER wins (we win!)
        ('PLAYER', 'BANKER'),  # Follow PLAYER, BANKER wins (we lose)
        ('BANKER', 'BANKER'),  # Maintain BANKER, BANKER wins (we win!)
        ('BANKER', 'BANKER'),  # Follow BANKER, BANKER wins (we win!) - Press streak
        ('BANKER', 'BANKER'),  # Maintain BANKER (press), BANKER wins (we win!)
        ('BANKER', 'PLAYER'),  # Maintain BANKER (press), PLAYER wins (we lose)
    ]
    
    hand_num = 1
    total_pnl = 0
    
    for our_bet, winner in hands:
        decision = BaccaratStrategist.get_next_decision(state)
        bet_target = decision['bet_target']
        bet_amount = decision['bet_amount']
        
        # Simulate outcome
        won = (bet_target == winner)
        pnl = bet_amount * 0.95 if (won and winner == 'BANKER') else (bet_amount if won else -bet_amount)
        total_pnl += pnl
        
        result = "WIN ✓" if won else "LOSS ❌"
        
        print(f"{hand_num:<6} {bet_target:<12} {winner:<10} {result:<8} ${pnl:>+6.0f} {state.consecutive_losses:<8} {state.current_press_streak:<6}")
        
        # Update state
        BaccaratStrategist.update_state_after_hand(state, won, pnl, False, winner)
        
        hand_num += 1
    
    print("-"*70)
    print(f"Total P&L: ${total_pnl:+.0f}")
    print()
    
    print("KEY OBSERVATIONS:")
    print("="*70)
    print("• Hand 1: Start with BANKER (default)")
    print("• Hand 2: Switch to PLAYER (follow winner)")
    print("• Hand 3: MAINTAIN BANKER despite PLAYER winning last (in losing progression)")
    print("• Hand 5: MAINTAIN PLAYER in progression, then win resets")
    print("• Hand 6: Follow winner again after progression ends")
    print("• Hands 8-9: Maintain bet during winning press streak")
    print()
    print("✓ FOLLOW_WINNER adapts to table dynamics while respecting progressions")
    print()

if __name__ == '__main__':
    demo_follow_winner()
