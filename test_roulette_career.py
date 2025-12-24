#!/usr/bin/env python3
"""
Test Roulette career simulation
"""
import sys
from ui.career_mode import CareerManager
from engine.strategy_rules import StrategyOverrides, PlayMode

def test_roulette_career():
    """Test a complete career simulation with Roulette"""
    print("=" * 60)
    print("ROULETTE CAREER SIMULATION TEST")
    print("=" * 60)
    
    # Create a Roulette strategy config
    config = {
        'tac_mode': 'Standard',
        'tac_safety': 25,
        'tac_base_bet': 5.0,
        'tac_bet': 'Red',  # Roulette bet
        'tac_iron': 3,
        'tac_press': 1,
        'tac_depth': 3,
        'tac_shoes': 3,
        'tac_penalty': True,
        'risk_stop': 10,
        'risk_prof': 10,
        'risk_ratch': False,
        'risk_ratch_mode': 'Standard',
        'eco_win': 300,
        'eco_loss': 300,
        'eco_tax': False,
        'eco_hol': False,
        'eco_hol_ceil': 10000,
        'eco_insolvency': 1000,
        'eco_tax_thresh': 12500,
        'eco_tax_rate': 25
    }
    
    sequence_config = [{
        'strategy_name': 'Test Roulette',
        'target_ga': 50000,
        'config': config
    }]
    
    start_ga = 10000
    total_years = 1
    sessions_per_year = 12
    
    print(f"  Start GA: €{start_ga:,.0f}")
    print(f"  Years: {total_years}")
    print(f"  Sessions/year: {sessions_per_year}")
    print(f"  Game: Roulette (Red)")
    print("\nRunning simulation...")
    
    try:
        traj, log, final_ga, total_in = CareerManager.run_compound_career(
            sequence_config, start_ga, total_years, sessions_per_year
        )
        
        print(f"\n✓ Simulation completed successfully!")
        print(f"  Start GA: €{start_ga:,.0f}")
        print(f"  Final GA: €{final_ga:,.0f}")
        print(f"  Total Input: €{total_in:,.0f}")
        print(f"  Net P&L: €{final_ga - start_ga:,.0f}")
        print(f"  Trajectory Length: {len(traj)} months")
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_roulette_career()
    sys.exit(0 if success else 1)
