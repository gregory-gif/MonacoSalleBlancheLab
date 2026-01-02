#!/usr/bin/env python3
"""
Debug test for Negatif 1-2-4-7 Snap-Back progression.
Manually traces through several spins to see bet behavior.
"""

import random
from engine.roulette_rules import (
    RouletteSessionState, RouletteStrategist, RouletteBet, WINNING_NUMBERS,
    create_spice_engine_from_overrides
)
from engine.tier_params import TierConfig
from engine.strategy_rules import StrategyOverrides

# Set seed for reproducibility
random.seed(42)

def test_snapback_detailed():
    """Test with detailed spin-by-spin output"""
    
    base_bet = 5.0
    tier = TierConfig(
        level=1, min_ga=0, max_ga=100000,
        base_unit=base_bet, press_unit=base_bet,
        stop_loss=-500, profit_lock=200, catastrophic_cap=-1000
    )
    
    overrides = StrategyOverrides(
        shoes_per_session=1,
        stop_loss_units=50,
        profit_lock_units=30,
        press_trigger_wins=7,  # Negatif 1-2-4-7 Snap-Back
        press_depth=3,
        iron_gate_limit=5,
        ratchet_enabled=False,
        bet_strategy='Red',
        bet_strategy_2='Odd'
    )
    
    state = RouletteSessionState(tier=tier, overrides=overrides)
    state.spice_engine = create_spice_engine_from_overrides(overrides, base_bet)
    
    active_bets = [RouletteBet.RED, RouletteBet.ODD]
    
    print("=" * 80)
    print("DETAILED SNAP-BACK PROGRESSION TEST")
    print("=" * 80)
    print(f"Base Bet: €{base_bet}")
    print(f"Bets: Red (index 0) + Odd (index 1)")
    print(f"Progression: 1-2-4-7 (on losses)")
    print("=" * 80)
    print()
    
    for spin_num in range(1, 21):
        # Get decision
        decision = RouletteStrategist.get_next_decision(state)
        if decision['mode'] == 'STOPPED':
            print(f"Session stopped: {decision['reason']}")
            break
        
        unit_amt = decision['bet']
        
        # Determine active bets
        use_snapback_halt = len(active_bets) == 2
        if use_snapback_halt and state.bet_in_progression >= 0:
            current_bets = [active_bets[state.bet_in_progression]]
        else:
            current_bets = active_bets.copy()
        
        print(f"Spin {spin_num}:")
        print(f"  Progression State: Level={state.neg_snapback_level}, "
              f"Bet in Prog={state.bet_in_progression}")
        print(f"  Bet Amount: €{unit_amt}")
        print(f"  Active Bets: {[b.name for b in current_bets]}")
        
        # Resolve
        if use_snapback_halt:
            number, won_main, pnl_main, individual_results = \
                RouletteStrategist.resolve_spin_with_individual_tracking(
                    state, current_bets, unit_amt
                )
            
            print(f"  Number: {number}")
            print(f"  Individual Results:")
            for bet_type, pnl, won in individual_results:
                color = WINNING_NUMBERS.get(bet_type, set())
                hit = "HIT" if won else "MISS"
                print(f"    {bet_type.name}: {hit} (€{pnl:+.2f})")
            
            # Update snap-back state
            if state.bet_in_progression == -1:
                # Check if any bet lost
                for idx, (bet_type, pnl, won) in enumerate(individual_results):
                    if not won:
                        # Find which bet this is
                        for j, active_bet in enumerate(active_bets):
                            if active_bet == bet_type:
                                state.bet_in_progression = j
                                state.neg_snapback_level = 1
                                print(f"  → {bet_type.name} entered progression (index {j})")
                                break
                        break
            else:
                # Bet in progression - check result
                if individual_results:
                    bet_result = individual_results[0]
                    if bet_result[2]:  # Won
                        print(f"  → Progression WON! Reset to both bets")
                        state.neg_snapback_level = 0
                        state.bet_in_progression = -1
                    else:  # Lost
                        state.neg_snapback_level += 1
                        if state.neg_snapback_level > 3:
                            print(f"  → Progression FAILED (max level)! Reset to both bets")
                            state.neg_snapback_level = 0
                            state.bet_in_progression = -1
                        else:
                            print(f"  → Progression continues at level {state.neg_snapback_level}")
        else:
            number, won_main, pnl_main = RouletteStrategist.resolve_spin(
                state, current_bets, unit_amt
            )
            print(f"  Number: {number}")
        
        print(f"  Spin P&L: €{pnl_main:+.2f}")
        print(f"  Session P&L: €{state.session_pnl:+.2f}")
        print()
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    test_snapback_detailed()
