#!/usr/bin/env python3
"""
Full career simulation test
"""
import sys
import traceback
from ui.career_mode import CareerManager
from utils.persistence import load_profile

def test_full_career():
    """Test a complete career simulation"""
    print("=" * 60)
    print("FULL CAREER SIMULATION TEST")
    print("=" * 60)
    
    try:
        # Load profile
        profile = load_profile()
        saved_strats = profile.get('saved_strategies', {})
        
        if not saved_strats:
            print("✗ No saved strategies found!")
            return False
        
        # Get first strategy
        first_strat_name = list(saved_strats.keys())[0]
        first_config = saved_strats[first_strat_name]
        
        print(f"✓ Using strategy: {first_strat_name}")
        
        # Set up sequence config
        sequence_config = [{
            'strategy_name': first_strat_name,
            'target_ga': 50000,
            'config': first_config
        }]
        
        # Run career simulation
        start_ga = 10000
        total_years = 1
        sessions_per_year = 12
        
        print(f"  Start GA: €{start_ga:,.0f}")
        print(f"  Years: {total_years}")
        print(f"  Sessions/year: {sessions_per_year}")
        print("\nRunning simulation...")
        
        traj, log, final_ga, total_in = CareerManager.run_compound_career(
            sequence_config, start_ga, total_years, sessions_per_year
        )
        
        print(f"\n✓ Simulation completed successfully!")
        print(f"  Start GA: €{start_ga:,.0f}")
        print(f"  Final GA: €{final_ga:,.0f}")
        print(f"  Total Input: €{total_in:,.0f}")
        print(f"  Net P&L: €{final_ga - start_ga:,.0f}")
        print(f"  Trajectory Length: {len(traj)} months")
        print(f"  Log Events: {len(log)}")
        
        # Show some log entries
        if log:
            print("\nLog Sample:")
            for entry in log[:5]:
                print(f"  Month {entry['month']}: {entry['event']} - {entry['details']}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error running career simulation: {e}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_full_career()
    sys.exit(0 if success else 1)
