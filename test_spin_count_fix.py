"""
Test to verify that spin counts less than 60 (e.g., 0.5 shoes = 30 spins) work correctly
"""

from engine.strategy_rules import StrategyOverrides
from engine.tier_params import generate_tier_map, get_tier_for_ga
from ui.roulette_sim import RouletteWorker

def test_low_spin_counts():
    """Test that sessions with less than 60 spins work correctly"""
    
    print("=" * 70)
    print("SPIN COUNT FIX TEST - Testing values less than 60 spins")
    print("=" * 70)
    
    # Test various shoes_per_session values
    test_values = [0.5, 0.75, 1.0, 1.5, 2.0]
    
    for shoes_value in test_values:
        expected_spins = int(shoes_value * 60)
        
        print(f"\n{'='*70}")
        print(f"Testing shoes_per_session = {shoes_value} (Expected: {expected_spins} spins)")
        print('='*70)
        
        # Create overrides with the test value
        overrides = StrategyOverrides(
            iron_gate_limit=3,
            stop_loss_units=10,
            profit_lock_units=10,
            press_trigger_wins=1,
            press_depth=3,
            bet_strategy='Red',
            bet_strategy_2=None,
            shoes_per_session=shoes_value,  # Test value as float
            penalty_box_enabled=True,
            ratchet_enabled=False,
        )
        
        # Test parameters
        start_ga = 2000
        tier_map = generate_tier_map(25, mode='Standard', game_type='Roulette', base_bet=5.0)
        tier = get_tier_for_ga(start_ga, tier_map, 1, 'Standard', game_type='Roulette')
        base_bet_val = 5.0
        
        # Run a single session
        result = RouletteWorker.run_session(
            current_ga=start_ga,
            overrides=overrides,
            tier_map=tier_map,
            use_ratchet=False,
            penalty_mode=False,
            active_level=tier.level,
            mode='Standard',
            base_bet=base_bet_val,
            track_spins=False
        )
        
        pnl, vol, used_level, spins, spice_stats, exit_reason, max_caroline, max_dalembert, final_streak, peak_profit = result
        
        # Display results
        print(f"  shoes_per_session value: {shoes_value}")
        print(f"  Expected max spins: {expected_spins}")
        print(f"  Actual spins played: {spins}")
        print(f"  Session PnL: €{pnl:+,.2f}")
        print(f"  Exit reason: {exit_reason}")
        
        # Verify the session actually played
        if spins > 0:
            print(f"  ✅ SUCCESS: Session played {spins} spins (not 0!)")
        else:
            print(f"  ❌ FAILED: Session resulted in 0 spins")
    
    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)

if __name__ == "__main__":
    test_low_spin_counts()
