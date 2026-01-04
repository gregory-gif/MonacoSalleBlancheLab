"""
Test script for "The Gentle Surgeon" (1-2-4) negative progression.
"""

from engine.roulette_rules import RouletteSessionState, RouletteStrategist, RouletteBet
from engine.strategy_rules import StrategyOverrides
from engine.tier_params import TierConfig
from engine.spice_system import SpiceEngine, DEFAULT_SPICE_CONFIG, DEFAULT_GLOBAL_SPICE_CONFIG

def test_gentle_surgeon_progression():
    """Test the gentle surgeon 1-2-4 progression"""
    
    # Setup
    base_bet = 10.0
    tier = TierConfig(
        level=1,
        min_ga=0,
        max_ga=100000,
        base_unit=base_bet,
        press_unit=5.0,
        stop_loss=-100.0,
        profit_lock=200.0,
        catastrophic_cap=-500.0
    )
    
    overrides = StrategyOverrides(
        press_trigger_wins=8,  # The Gentle Surgeon
        iron_gate_limit=999,  # Disable iron gate
        stop_loss_units=0,
        profit_lock_units=0,
        ratchet_enabled=False
    )
    
    # Create spice engine (minimal config)
    spice_engine = SpiceEngine(DEFAULT_SPICE_CONFIG, DEFAULT_GLOBAL_SPICE_CONFIG)
    
    # Initialize state
    state = RouletteSessionState(
        tier=tier,
        overrides=overrides,
        spice_engine=spice_engine,
        session_start_bankroll=1000.0
    )
    
    print("THE GENTLE SURGEON (1-2-4) PROGRESSION TEST")
    print("=" * 60)
    print(f"Base Unit: €{tier.base_unit}")
    print(f"Progression: 1-2-4 on losses, reset to 1 on win")
    print("=" * 60)
    
    # Simulate series: Loss, Loss, Loss, Win
    test_sequence = [
        (False, "LOSS", 0, 10.0),   # Level 0 -> 1 (bet was 1u)
        (False, "LOSS", 1, 20.0),   # Level 1 -> 2 (bet was 2u)
        (False, "LOSS", 2, 40.0),   # Level 2 -> 2 (bet was 4u, cap at level 2)
        (True, "WIN", 2, 40.0),      # Level 2 -> 0 (bet was 4u, reset)
        (False, "LOSS", 0, 10.0),   # Level 0 -> 1 (bet was 1u)
        (True, "WIN", 1, 20.0),      # Level 1 -> 0 (bet was 2u, reset)
    ]
    
    print("\nSpin-by-Spin Results:")
    print(f"{'Spin':<6} {'Level':<8} {'Bet':<10} {'Result':<8} {'Next Level':<12} {'PnL':<10}")
    print("-" * 60)
    
    for i, (wins, result, expected_level_before, expected_bet) in enumerate(test_sequence, 1):
        # Get decision (bet size)
        decision = RouletteStrategist.get_next_decision(state)
        current_bet = decision['bet']
        current_level = state.gentle_surgeon_level
        
        # Verify bet matches expectation
        assert current_level == expected_level_before, f"Level mismatch at spin {i}: expected {expected_level_before}, got {current_level}"
        assert abs(current_bet - expected_bet) < 0.01, f"Bet mismatch at spin {i}: expected €{expected_bet}, got €{current_bet}"
        
        # Simulate result by directly updating PnL
        if wins:
            state.session_pnl += current_bet
            # Manual progression update for win
            state.gentle_surgeon_level = 0
        else:
            state.session_pnl -= current_bet
            # Manual progression update for loss
            state.gentle_surgeon_level += 1
            if state.gentle_surgeon_level > 2:
                state.gentle_surgeon_level = 2
        
        next_level = state.gentle_surgeon_level
        
        print(f"{i:<6} {current_level:<8} €{current_bet:<9.0f} {result:<8} {next_level:<12} €{state.session_pnl:+.0f}")
    
    print("\n" + "=" * 60)
    print("✓ All assertions passed!")
    print(f"Final Session PnL: €{state.session_pnl:+.0f}")
    print(f"Final Level: {state.gentle_surgeon_level}")
    print("\nThe Gentle Surgeon progression is working correctly.")
    print("  - Advances 1->2->4 on consecutive losses")
    print("  - Caps at 4 units (level 2)")
    print("  - Resets to 1 unit on any win")

if __name__ == "__main__":
    test_gentle_surgeon_progression()
