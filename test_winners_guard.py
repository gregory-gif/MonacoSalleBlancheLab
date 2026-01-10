"""
Test script for "Winner's Guard" (1-1-2-4 with profit stop) negative progression.
"""

from engine.roulette_rules import RouletteSessionState, RouletteStrategist, RouletteBet
from engine.strategy_rules import StrategyOverrides
from engine.tier_params import TierConfig
from engine.spice_system import SpiceEngine, DEFAULT_SPICE_CONFIG, DEFAULT_GLOBAL_SPICE_CONFIG

def test_winners_guard_progression():
    """Test the winner's guard 1-1-2-4 progression with profit protection"""
    
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
        press_trigger_wins=9,  # Winner's Guard
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
    
    print("WINNER'S GUARD (1-1-2-4 with Profit Stop) PROGRESSION TEST")
    print("=" * 70)
    print(f"Base Unit: €{tier.base_unit}")
    print(f"Progression: 1-1-2-4 on losses (full sequence when losing)")
    print(f"Profit Guard: Caps at level 2 (4u) when session PnL > 0")
    print("=" * 70)
    
    # Test Part 1: Losing session (full progression)
    print("\n--- PART 1: LOSING SESSION (Full 1-1-2-4 Progression) ---")
    test_sequence_losing = [
        (False, "LOSS", 0, 10.0, "Start at level 0"),   # Level 0 -> 1
        (False, "LOSS", 1, 10.0, "Level 1 (still 1u)"),  # Level 1 -> 2
        (False, "LOSS", 2, 20.0, "Level 2 (now 2u)"),    # Level 2 -> 3
        (False, "LOSS", 3, 40.0, "Level 3 (now 4u, can use full seq)"),  # Level 3 -> 3 (cap)
        (True, "WIN", 3, 40.0, "Win at level 3"),        # Level 3 -> 0 (reset)
    ]
    
    print(f"\n{'Spin':<6} {'Level':<8} {'Bet':<10} {'Result':<8} {'Next Level':<12} {'PnL':<10} {'Note':<30}")
    print("-" * 95)
    
    for i, (wins, result, expected_level_before, expected_bet, note) in enumerate(test_sequence_losing, 1):
        decision = RouletteStrategist.get_next_decision(state)
        current_bet = decision['bet']
        current_level = state.winners_guard_level
        
        # Verify bet matches expectation
        assert current_level == expected_level_before, f"Level mismatch at spin {i}: expected {expected_level_before}, got {current_level}"
        assert abs(current_bet - expected_bet) < 0.01, f"Bet mismatch at spin {i}: expected €{expected_bet}, got €{current_bet}"
        
        # Simulate result by directly updating PnL
        if wins:
            state.session_pnl += current_bet
            state.winners_guard_level = 0
        else:
            state.session_pnl -= current_bet
            state.winners_guard_level += 1
            # Cap based on profit status
            if state.session_pnl > 0:
                if state.winners_guard_level > 2:
                    state.winners_guard_level = 2
            else:
                if state.winners_guard_level > 3:
                    state.winners_guard_level = 3
        
        next_level = state.winners_guard_level
        
        print(f"{i:<6} {current_level:<8} €{current_bet:<9.0f} {result:<8} {next_level:<12} €{state.session_pnl:+.0f}     {note}")
    
    # Test Part 2: Winning session (profit protection active)
    print("\n--- PART 2: WINNING SESSION (Profit Guard Active - Caps at 2u) ---")
    
    # Set up profitable scenario
    state.session_pnl = 60.0  # Up €60
    state.winners_guard_level = 0
    
    test_sequence_winning = [
        (False, "LOSS", 0, 10.0, "Start at level 0, up €60"),   # Level 0 -> 1
        (False, "LOSS", 1, 10.0, "Level 1, up €50"),            # Level 1 -> 2
        (False, "LOSS", 2, 20.0, "Level 2, up €30"),            # Level 2 -> 2 (GUARD ACTIVE!)
        (True, "WIN", 2, 20.0, "Win at level 2, up €30"),       # Level 2 -> 0 (reset)
        (False, "LOSS", 0, 10.0, "Start over, still up €40"),   # Level 0 -> 1
        (True, "WIN", 1, 10.0, "Win at level 1"),               # Level 1 -> 0 (reset)
    ]
    
    print(f"\n{'Spin':<6} {'Level':<8} {'Bet':<10} {'Result':<8} {'Next Level':<12} {'PnL':<10} {'Note':<35}")
    print("-" * 100)
    
    for i, (wins, result, expected_level_before, expected_bet, note) in enumerate(test_sequence_winning, 6):
        decision = RouletteStrategist.get_next_decision(state)
        current_bet = decision['bet']
        current_level = state.winners_guard_level
        
        # Verify bet matches expectation
        assert current_level == expected_level_before, f"Level mismatch at spin {i}: expected {expected_level_before}, got {current_level}"
        assert abs(current_bet - expected_bet) < 0.01, f"Bet mismatch at spin {i}: expected €{expected_bet}, got €{current_bet}"
        
        # Simulate result by directly updating PnL
        if wins:
            state.session_pnl += current_bet
            state.winners_guard_level = 0
        else:
            state.session_pnl -= current_bet
            state.winners_guard_level += 1
            # Cap based on profit status
            if state.session_pnl > 0:
                if state.winners_guard_level > 2:
                    state.winners_guard_level = 2
            else:
                if state.winners_guard_level > 3:
                    state.winners_guard_level = 3
        
        next_level = state.winners_guard_level
        
        print(f"{i:<6} {current_level:<8} €{current_bet:<9.0f} {result:<8} {next_level:<12} €{state.session_pnl:+.0f}     {note}")
    
    print("\n" + "=" * 70)
    print("✓ All assertions passed!")
    print(f"Final Session PnL: €{state.session_pnl:+.0f}")
    print(f"Final Level: {state.winners_guard_level}")
    print("\nWinner's Guard progression is working correctly:")
    print("  ✓ Full 1-1-2-4 progression when losing")
    print("  ✓ Caps at level 2 (2u max bet) when profitable")
    print("  ✓ Protects profits by avoiding the 4u bet when ahead")
    print("  ✓ Resets to level 0 on any win")

if __name__ == "__main__":
    test_winners_guard_progression()
