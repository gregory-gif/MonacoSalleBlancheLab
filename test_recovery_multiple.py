"""
Test script to demonstrate Recovery Session System with multiple simulations
"""

from engine.strategy_rules import StrategyOverrides
from engine.tier_params import generate_tier_map
from ui.roulette_sim import RouletteWorker

def test_recovery_sessions_multiple_runs():
    """Run multiple simulations to see recovery sessions in action"""
    
    print("=" * 70)
    print("RECOVERY SESSION SYSTEM - MULTIPLE RUN TEST")
    print("=" * 70)
    
    # Create overrides with recovery enabled
    overrides = StrategyOverrides(
        iron_gate_limit=3,
        stop_loss_units=10,
        profit_lock_units=20,  # Higher target to encourage losses
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
    total_months = 3  # 3 months
    sessions_per_year = 24  # 2 sessions per month
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
    
    num_simulations = 5
    
    print(f"\nConfiguration:")
    print(f"  Starting Capital: €{start_ga:,}")
    print(f"  Base Bet: €{base_bet_val}")
    print(f"  Regular Stop Loss: {overrides.stop_loss_units}u (€{overrides.stop_loss_units * base_bet_val:.0f})")
    print(f"  Recovery Stop Loss: {overrides.recovery_stop_loss}u (€{overrides.recovery_stop_loss * base_bet_val:.0f})")
    print(f"  Recovery Enabled: {overrides.recovery_enabled}")
    print(f"  Months: {total_months}")
    print(f"  Sessions/Year: {sessions_per_year}")
    
    total_recovery_sessions = 0
    total_normal_sessions = 0
    
    for sim_num in range(1, num_simulations + 1):
        print(f"\n{'='*70}")
        print(f"SIMULATION #{sim_num}")
        print('='*70)
        
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
            track_y1_details=True
        )
        
        recovery_count = 0
        normal_count = 0
        
        print(f"\nSession Details:")
        for entry in result['y1_log']:
            is_recovery = entry.get('is_recovery', False)
            if is_recovery:
                recovery_count += 1
                session_label = f"M{entry['month']} S{entry['session']} bis"
            else:
                normal_count += 1
                session_label = f"M{entry['month']} S{entry['session']}"
            
            result_emoji = "✅" if entry['result'] >= 0 else "❌"
            print(f"  {result_emoji} {session_label}: €{entry['result']:+,.0f} ({entry['spins']} spins, {entry['exit']})")
        
        print(f"\nSim #{sim_num} Summary:")
        print(f"  Final GA: €{result['final_ga']:,.2f}")
        print(f"  Normal Sessions: {normal_count}")
        print(f"  Recovery Sessions: {recovery_count}")
        
        total_recovery_sessions += recovery_count
        total_normal_sessions += normal_count
    
    print(f"\n{'='*70}")
    print("OVERALL SUMMARY")
    print('='*70)
    print(f"Total Simulations: {num_simulations}")
    print(f"Total Normal Sessions: {total_normal_sessions}")
    print(f"Total Recovery Sessions: {total_recovery_sessions}")
    print(f"Recovery Session Rate: {(total_recovery_sessions/total_normal_sessions)*100:.1f}%")
    
    if total_recovery_sessions > 0:
        print(f"\n✅ SUCCESS: {total_recovery_sessions} recovery sessions were triggered!")
    else:
        print(f"\n⚠️  INFO: No recovery sessions triggered (all sessions were positive)")
    
    print("="*70)

if __name__ == "__main__":
    test_recovery_sessions_multiple_runs()
