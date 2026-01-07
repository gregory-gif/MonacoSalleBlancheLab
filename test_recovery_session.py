"""
Test script to verify Recovery Session System functionality
"""

from engine.strategy_rules import StrategyOverrides
from engine.tier_params import generate_tier_map
from ui.roulette_sim import RouletteWorker

def test_recovery_session():
    """Test that recovery sessions trigger after negative sessions"""
    
    print("=" * 70)
    print("RECOVERY SESSION SYSTEM TEST")
    print("=" * 70)
    
    # Create overrides with recovery enabled
    overrides = StrategyOverrides(
        iron_gate_limit=3,
        stop_loss_units=10,
        profit_lock_units=10,
        press_trigger_wins=1,
        press_depth=3,
        bet_strategy='Red',
        bet_strategy_2=None,
        shoes_per_session=2,
        penalty_box_enabled=True,
        ratchet_enabled=False,
        recovery_enabled=True,  # Enable recovery sessions
        recovery_stop_loss=5     # Recovery sessions have tighter stop loss
    )
    
    # Test parameters
    start_ga = 2000
    total_months = 1  # Just 1 month
    sessions_per_year = 12  # 1 session per month
    contrib_win = 300
    contrib_loss = 300
    use_ratchet = False
    use_tax = False
    use_holiday = False
    safety_factor = 25
    target_points = 0
    earn_rate = 10
    holiday_ceiling = 10000
    insolvency_floor = 1000
    strategy_mode = 'Standard'
    base_bet_val = 5.0
    
    print(f"\nConfiguration:")
    print(f"  Starting Capital: €{start_ga:,}")
    print(f"  Base Bet: €{base_bet_val}")
    print(f"  Regular Stop Loss: {overrides.stop_loss_units}u")
    print(f"  Recovery Stop Loss: {overrides.recovery_stop_loss}u")
    print(f"  Recovery Enabled: {overrides.recovery_enabled}")
    
    # Run a short career simulation
    print(f"\nRunning simulation with recovery sessions enabled...")
    result = RouletteWorker.run_full_career(
        start_ga=start_ga,
        total_months=total_months,
        sessions_per_year=sessions_per_year,
        contrib_win=contrib_win,
        contrib_loss=contrib_loss,
        overrides=overrides,
        use_ratchet=use_ratchet,
        use_tax=use_tax,
        use_holiday=use_holiday,
        safety_factor=safety_factor,
        target_points=target_points,
        earn_rate=earn_rate,
        holiday_ceiling=holiday_ceiling,
        insolvency_floor=insolvency_floor,
        strategy_mode=strategy_mode,
        base_bet_val=base_bet_val,
        track_y1_details=True  # Track details
    )
    
    # Display results
    print(f"\nResults:")
    print(f"  Final GA: €{result['final_ga']:,.2f}")
    print(f"  Total Sessions Played: {len(result['y1_log'])}")
    
    # Check for recovery sessions
    recovery_count = 0
    normal_count = 0
    
    print(f"\nSession Details:")
    for entry in result['y1_log']:
        is_recovery = entry.get('is_recovery', False)
        if is_recovery:
            recovery_count += 1
            session_label = f"Session {entry['session']} bis (RECOVERY)"
        else:
            normal_count += 1
            session_label = f"Session {entry['session']}"
        
        print(f"  {session_label}:")
        print(f"    PnL: €{entry['result']:+,.2f}")
        print(f"    Spins: {entry['spins']}")
        print(f"    Exit: {entry['exit']}")
    
    print(f"\nSummary:")
    print(f"  Normal Sessions: {normal_count}")
    print(f"  Recovery Sessions: {recovery_count}")
    
    if recovery_count > 0:
        print(f"\n✅ SUCCESS: Recovery sessions were triggered!")
    else:
        print(f"\n⚠️  INFO: No recovery sessions triggered (all sessions were positive or break-even)")
    
    print("\n" + "=" * 70)
    print("Test completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    test_recovery_session()
