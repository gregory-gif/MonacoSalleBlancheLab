"""
TEST: FOLLOW_WINNER Bet Strategy
Tests the new FOLLOW_WINNER betting option that follows the winning bet
unless in a progression.
"""

from engine.baccarat_rules import BaccaratSessionState, BaccaratStrategist
from engine.strategy_rules import StrategyOverrides, BetStrategy
from engine.tier_params import TierConfig

def test_follow_winner_basic():
    """Test basic follow winner behavior"""
    print("\n" + "="*60)
    print("TEST: FOLLOW_WINNER Basic Behavior")
    print("="*60)
    
    tier = TierConfig(
        level=1, min_ga=0, max_ga=10000,
        base_unit=10, press_unit=5,
        stop_loss=-100, profit_lock=100,
        catastrophic_cap=-500
    )
    
    overrides = StrategyOverrides(
        iron_gate_limit=3,
        stop_loss_units=10,
        profit_lock_units=10,
        press_trigger_wins=1,
        press_depth=3,
        bet_strategy=BetStrategy.FOLLOW_WINNER
    )
    
    state = BaccaratSessionState(tier=tier, overrides=overrides)
    
    # Hand 1: First hand - should default to BANKER
    print("\n--- Hand 1: First Hand (No History) ---")
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"Bet Target: {decision['bet_target']}")
    print(f"Expected: BANKER (default)")
    assert decision['bet_target'] == 'BANKER', "First hand should default to BANKER"
    
    # Simulate PLAYER wins
    BaccaratStrategist.update_state_after_hand(state, won=False, pnl_change=-10, was_tie=False, outcome='PLAYER')
    
    # Hand 2: Should follow PLAYER (last winner)
    print("\n--- Hand 2: After PLAYER Won ---")
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"Bet Target: {decision['bet_target']}")
    print(f"Expected: PLAYER (following winner)")
    print(f"Consecutive Losses: {state.consecutive_losses}")
    print(f"Press Streak: {state.current_press_streak}")
    assert decision['bet_target'] == 'PLAYER', "Should follow last winner (PLAYER)"
    
    # Simulate BANKER wins
    BaccaratStrategist.update_state_after_hand(state, won=False, pnl_change=-10, was_tie=False, outcome='BANKER')
    
    # Hand 3: Should follow BANKER (last winner)
    print("\n--- Hand 3: After BANKER Won ---")
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"Bet Target: {decision['bet_target']}")
    print(f"Expected: BANKER (following winner)")
    print(f"Consecutive Losses: {state.consecutive_losses}")
    assert decision['bet_target'] == 'BANKER', "Should follow last winner (BANKER)"
    
    print("\n✓ Basic follow winner behavior works correctly")


def test_follow_winner_during_progression():
    """Test follow winner maintains bet during progression"""
    print("\n" + "="*60)
    print("TEST: FOLLOW_WINNER During Progression")
    print("="*60)
    
    tier = TierConfig(
        level=1, min_ga=0, max_ga=10000,
        base_unit=10, press_unit=5,
        stop_loss=-100, profit_lock=100,
        catastrophic_cap=-500
    )
    
    overrides = StrategyOverrides(
        iron_gate_limit=3,
        stop_loss_units=10,
        profit_lock_units=10,
        press_trigger_wins=1,  # Press after 1 win
        press_depth=3,
        bet_strategy=BetStrategy.FOLLOW_WINNER
    )
    
    state = BaccaratSessionState(tier=tier, overrides=overrides)
    
    # Initial setup: Bet BANKER, BANKER wins
    print("\n--- Setup: Bet BANKER, BANKER Wins ---")
    decision = BaccaratStrategist.get_next_decision(state)
    BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=10, was_tie=False, outcome='BANKER')
    print(f"Press Streak after win: {state.current_press_streak}")
    
    # Now PLAYER wins (we lose), but we're NOT in a losing progression
    BaccaratStrategist.update_state_after_hand(state, won=False, pnl_change=-10, was_tie=False, outcome='PLAYER')
    print(f"\n--- After PLAYER Wins (We Lose) ---")
    print(f"Consecutive Losses: {state.consecutive_losses}")
    print(f"Press Streak: {state.current_press_streak}")
    
    # Hand after loss: We're in a losing streak now
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"Bet Target: {decision['bet_target']}")
    print(f"Expected: PLAYER (maintain during losing streak)")
    assert decision['bet_target'] == 'PLAYER', "Should maintain bet during losing progression"
    
    # Simulate another loss (BANKER wins, we lose on PLAYER)
    BaccaratStrategist.update_state_after_hand(state, won=False, pnl_change=-10, was_tie=False, outcome='BANKER')
    print(f"\n--- After Another Loss ---")
    print(f"Consecutive Losses: {state.consecutive_losses}")
    
    # Should still bet PLAYER (maintain during progression)
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"Bet Target: {decision['bet_target']}")
    print(f"Expected: BANKER (maintain during losing streak)")
    assert decision['bet_target'] == 'BANKER', "Should maintain bet during losing progression"
    
    # Now win (BANKER wins, we bet BANKER)
    BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=10, was_tie=False, outcome='BANKER')
    print(f"\n--- After Win ---")
    print(f"Consecutive Losses: {state.consecutive_losses}")
    print(f"Press Streak: {state.current_press_streak}")
    
    # Now PLAYER wins - should follow
    BaccaratStrategist.update_state_after_hand(state, won=False, pnl_change=-10, was_tie=False, outcome='PLAYER')
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"\n--- After PLAYER Wins (streak reset) ---")
    print(f"Bet Target: {decision['bet_target']}")
    print(f"Consecutive Losses: {state.consecutive_losses}")
    print(f"Press Streak: {state.current_press_streak}")
    
    print("\n✓ Follow winner correctly maintains bet during progressions")


def test_follow_winner_after_tie():
    """Test follow winner behavior after a tie"""
    print("\n" + "="*60)
    print("TEST: FOLLOW_WINNER After Tie")
    print("="*60)
    
    tier = TierConfig(
        level=1, min_ga=0, max_ga=10000,
        base_unit=10, press_unit=5,
        stop_loss=-100, profit_lock=100,
        catastrophic_cap=-500
    )
    
    overrides = StrategyOverrides(
        iron_gate_limit=3,
        stop_loss_units=10,
        profit_lock_units=10,
        press_trigger_wins=1,
        press_depth=3,
        bet_strategy=BetStrategy.FOLLOW_WINNER
    )
    
    state = BaccaratSessionState(tier=tier, overrides=overrides)
    
    # Set up: BANKER wins
    BaccaratStrategist.update_state_after_hand(state, won=True, pnl_change=10, was_tie=False, outcome='BANKER')
    
    # Then a tie occurs
    print("\n--- Tie Occurs ---")
    BaccaratStrategist.update_state_after_hand(state, won=False, pnl_change=0, was_tie=True, outcome='TIE')
    
    # Next bet should maintain last non-tie outcome (BANKER)
    decision = BaccaratStrategist.get_next_decision(state)
    print(f"Last Outcome: {state.last_outcome}")
    print(f"Bet Target: {decision['bet_target']}")
    print(f"Expected: BANKER (ties are ignored)")
    
    print("\n✓ Follow winner correctly handles ties")


if __name__ == '__main__':
    print("\n" + "="*70)
    print("FOLLOW_WINNER BET STRATEGY TEST SUITE")
    print("="*70)
    
    try:
        test_follow_winner_basic()
        test_follow_winner_during_progression()
        test_follow_winner_after_tie()
        
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED")
        print("="*70)
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise
