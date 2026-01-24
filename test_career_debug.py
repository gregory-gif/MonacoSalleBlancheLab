#!/usr/bin/env python3
"""
Debug script to test career mode simulation
"""
import sys
import traceback
from engine.strategy_rules import StrategyOverrides, BetStrategy, PlayMode
from engine.tier_params import generate_tier_map, get_tier_for_ga
from ui.simulator import BaccaratWorker
from ui.roulette_sim import RouletteWorker
from utils.persistence import load_profile

def test_career_simulation():
    """Test a simple career simulation"""
    print("=" * 60)
    print("CAREER MODE DEBUG TEST")
    print("=" * 60)
    
    # Load profile
    try:
        profile = load_profile()
        print(f"✓ Profile loaded successfully")
        saved_strats = profile.get('saved_strategies', {})
        print(f"✓ Found {len(saved_strats)} saved strategies")
        
        if not saved_strats:
            print("✗ No saved strategies found!")
            return False
            
        # Get first strategy
        first_strat_name = list(saved_strats.keys())[0]
        first_config = saved_strats[first_strat_name]
        print(f"✓ Testing with strategy: {first_strat_name}")
        print(f"  Config keys: {list(first_config.keys())}")
        
    except Exception as e:
        print(f"✗ Error loading profile: {e}")
        traceback.print_exc()
        return False
    
    # Extract parameters (similar to CareerManager._extract_params)
    try:
        mode = first_config.get('tac_mode', 'Standard')
        safety = first_config.get('tac_safety', 25)
        base_bet = first_config.get('tac_base_bet', 10.0)
        bet_val = first_config.get('tac_bet', 'Banker')
        
        # Detect game type
        ROULETTE_BETS = {'Red', 'Black', 'Even', 'Odd', '1-18', '19-36'}
        game_type = 'Roulette' if bet_val in ROULETTE_BETS else 'Baccarat'
        
        print(f"✓ Game Type: {game_type}")
        print(f"  Mode: {mode}")
        print(f"  Safety: {safety}")
        print(f"  Base Bet: €{base_bet}")
        print(f"  Bet: {bet_val}")
        
        # Generate tier map
        tier_map = generate_tier_map(safety, mode=mode, game_type=game_type, base_bet=base_bet)
        print(f"✓ Tier map generated: {len(tier_map)} tiers")
        
        # Create overrides
        if game_type == 'Baccarat':
            if bet_val == 'BANKER':
                bet_strat_obj = BetStrategy.BANKER
            elif bet_val == 'PLAYER':
                bet_strat_obj = BetStrategy.PLAYER
            elif bet_val == 'FOLLOW_WINNER':
                bet_strat_obj = BetStrategy.FOLLOW_WINNER
            else:
                bet_strat_obj = BetStrategy.BANKER
        else:
            bet_strat_obj = bet_val
        
        overrides = StrategyOverrides(
            iron_gate_limit=first_config.get('tac_iron', 3),
            stop_loss_units=first_config.get('risk_stop', 10),
            profit_lock_units=first_config.get('risk_prof', 10),
            press_trigger_wins=first_config.get('tac_press', 1),
            press_depth=first_config.get('tac_depth', 3),
            ratchet_enabled=first_config.get('risk_ratch', False),
            ratchet_mode=first_config.get('risk_ratch_mode', 'Standard'),
            shoes_per_session=first_config.get('tac_shoes', 3),
            bet_strategy=bet_strat_obj,
            penalty_box_enabled=first_config.get('tac_penalty', True)
            # Note: SPICE v5.0 parameters use defaults (all disabled by default)
        )
        
        print(f"✓ Strategy overrides created")
        
    except Exception as e:
        print(f"✗ Error creating strategy parameters: {e}")
        traceback.print_exc()
        return False
    
    # Test a single session
    try:
        current_ga = 10000.0
        active_level = 1
        use_ratchet = first_config.get('risk_ratch', False)
        use_penalty = first_config.get('tac_penalty', True)
        
        print(f"\n--- Running Test Session ---")
        print(f"  Starting GA: €{current_ga:,.0f}")
        print(f"  Level: {active_level}")
        print(f"  Use Ratchet: {use_ratchet}")
        print(f"  Use Penalty: {use_penalty}")
        
        if game_type == 'Roulette':
            pnl, vol, used_lvl, hands, exit_reason, press_streak = RouletteWorker.run_session(
                current_ga, overrides, tier_map, use_ratchet, use_penalty, active_level, mode, base_bet
            )
            print(f"✓ Roulette session completed")
            print(f"  P&L: €{pnl:,.2f}")
            print(f"  Volume: €{vol:,.2f}")
            print(f"  Level: {used_lvl}")
            print(f"  Hands: {hands}")
            print(f"  Exit: {exit_reason}")
        else:
            pnl, vol, used_lvl, hands, exit_reason, press_streak, tie_count, tie_bets, tie_pnl, _, _ = BaccaratWorker.run_session(
                current_ga, overrides, tier_map, use_ratchet, use_penalty, active_level, mode, base_bet
            )
            print(f"✓ Baccarat session completed")
            print(f"  P&L: €{pnl:,.2f}")
            print(f"  Volume: €{vol:,.2f}")
            print(f"  Level: {used_lvl}")
            print(f"  Hands: {hands}")
            print(f"  Exit: {exit_reason}")
            print(f"  Ties: {tie_count} | Tie Bets: {tie_bets} | Tie P&L: €{tie_pnl:,.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error running session: {e}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_career_simulation()
    sys.exit(0 if success else 1)
