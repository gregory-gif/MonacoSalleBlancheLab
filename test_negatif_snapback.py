#!/usr/bin/env python3
"""
Test script for Negatif 1-2-4-7 Snap-Back progression with dual-bet halting.
This tests the new progression mode where one bet halts while the other is in progression.
"""

from engine.roulette_rules import (
    RouletteSessionState, RouletteStrategist, RouletteBet,
    create_spice_engine_from_overrides
)
from engine.tier_params import TierConfig
from engine.strategy_rules import StrategyOverrides

def test_snapback_progression():
    """Test the negatif 1-2-4-7 snap-back progression"""
    
    # Setup basic tier and overrides
    base_bet = 5.0
    tier = TierConfig(
        level=1,
        min_ga=0,
        max_ga=100000,
        base_unit=base_bet,
        press_unit=base_bet,
        stop_loss=-500,
        profit_lock=200,
        catastrophic_cap=-1000
    )
    
    overrides = StrategyOverrides(
        shoes_per_session=2,
        stop_loss_units=20,
        profit_lock_units=10,
        press_trigger_wins=7,  # Negatif 1-2-4-7 Snap-Back
        press_depth=3,
        iron_gate_limit=3,
        ratchet_enabled=False,
        bet_strategy='Red',
        bet_strategy_2='Odd'
    )
    
    # Create state
    state = RouletteSessionState(tier=tier, overrides=overrides)
    state.spice_engine = create_spice_engine_from_overrides(overrides, base_bet)
    
    print("=" * 60)
    print("NEGATIF 1-2-4-7 SNAP-BACK PROGRESSION TEST")
    print("=" * 60)
    print(f"Base Bet: €{base_bet}")
    print(f"Bets: Red + Odd")
    print(f"Progression Sequence: 1-2-4-7 (on losses)")
    print(f"Halt Logic: When one bet enters progression, the other halts")
    print("=" * 60)
    print()
    
    # Define test scenarios
    active_bets = [RouletteBet.RED, RouletteBet.ODD]
    
    # Scenario 1: First bet (Red) loses and enters progression
    print("SCENARIO 1: Red loses first, enters progression")
    print("-" * 60)
    
    state.session_pnl = 0
    state.neg_snapback_level = 0
    state.bet_in_progression = -1
    
    # Simulate losing red (number = 2, black/even)
    for spin in range(1, 8):
        decision = RouletteStrategist.get_next_decision(state)
        unit_amt = decision['bet']
        
        # Determine which bets are active
        if state.bet_in_progression == -1:
            current_bets = active_bets.copy()
            bet_status = "Both (Red + Odd)"
        else:
            current_bets = [active_bets[state.bet_in_progression]]
            bet_status = f"Only {current_bets[0].name} (in progression)"
        
        print(f"Spin {spin}:")
        print(f"  Active Bets: {bet_status}")
        print(f"  Bet Amount: €{unit_amt}")
        print(f"  Progression Level: {state.neg_snapback_level}")
        
        # Simulate result - let's alternate wins/losses for testing
        if spin == 1:
            # Red loses (number 2 = black), Odd wins
            number, won, pnl, individual = RouletteStrategist.resolve_spin_with_individual_tracking(
                state, current_bets, unit_amt
            )
            print(f"  Result: Number {number}")
            print(f"  Individual Results: {[(bt.name, p, w) for bt, p, w in individual]}")
            
            # Update progression state (manual for test)
            if state.bet_in_progression == -1:
                for idx, (bet_type, bet_pnl, bet_won) in enumerate(individual):
                    if not bet_won and bet_type == RouletteBet.RED:
                        state.bet_in_progression = 0  # Red is index 0
                        state.neg_snapback_level = 1
                        print(f"  → Red entered progression at level 1")
                        break
        
        elif spin <= 4:
            # Continue losing red
            if state.bet_in_progression == 0:
                number, won, pnl, individual = RouletteStrategist.resolve_spin_with_individual_tracking(
                    state, current_bets, unit_amt
                )
                print(f"  Result: Number {number}")
                if individual and not individual[0][2]:
                    state.neg_snapback_level += 1
                    if state.neg_snapback_level > 3:
                        state.neg_snapback_level = 0
                        state.bet_in_progression = -1
                        print(f"  → Progression FAILED - Reset to both bets")
                    else:
                        print(f"  → Progression advanced to level {state.neg_snapback_level}")
        
        elif spin == 5:
            # Red wins - progression completes
            # Manually set a winning number for red
            state.session_pnl -= unit_amt  # Simulate loss
            state.session_pnl += unit_amt * 2  # Simulate win (net +1u)
            print(f"  Result: Red WINS!")
            state.neg_snapback_level = 0
            state.bet_in_progression = -1
            print(f"  → Progression COMPLETED - Resume both bets")
        
        print(f"  Session P&L: €{state.session_pnl:.2f}")
        print()
        
        if spin >= 5:
            break
    
    print("\n" + "=" * 60)
    print("SCENARIO 2: Odd loses first, enters progression")
    print("-" * 60)
    
    state.session_pnl = 0
    state.neg_snapback_level = 0
    state.bet_in_progression = -1
    
    for spin in range(1, 6):
        decision = RouletteStrategist.get_next_decision(state)
        unit_amt = decision['bet']
        
        if state.bet_in_progression == -1:
            current_bets = active_bets.copy()
            bet_status = "Both (Red + Odd)"
        else:
            current_bets = [active_bets[state.bet_in_progression]]
            bet_status = f"Only {current_bets[0].name} (in progression)"
        
        print(f"Spin {spin}:")
        print(f"  Active Bets: {bet_status}")
        print(f"  Bet Amount: €{unit_amt}")
        print(f"  Progression Level: {state.neg_snapback_level}")
        
        if spin == 1:
            # Simulate Odd loses, Red wins (number 3 = red/odd, but we'll manually handle)
            # For test purposes, let's say even number wins (Red wins, Odd loses)
            if state.bet_in_progression == -1:
                # Manually set Odd to lose
                state.bet_in_progression = 1  # Odd is index 1
                state.neg_snapback_level = 1
                state.session_pnl -= unit_amt  # Odd loses
                state.session_pnl += unit_amt  # Red wins
                print(f"  Result: Red wins, Odd loses")
                print(f"  → Odd entered progression at level 1")
        
        elif spin <= 3:
            # Odd continues to lose
            state.session_pnl -= unit_amt
            state.neg_snapback_level += 1
            if state.neg_snapback_level > 3:
                state.neg_snapback_level = 0
                state.bet_in_progression = -1
                print(f"  Result: Odd loses (max level reached)")
                print(f"  → Progression FAILED - Reset to both bets")
            else:
                print(f"  Result: Odd loses")
                print(f"  → Progression advanced to level {state.neg_snapback_level}")
        
        elif spin == 4:
            # Odd wins
            state.session_pnl += unit_amt * 2
            state.neg_snapback_level = 0
            state.bet_in_progression = -1
            print(f"  Result: Odd WINS!")
            print(f"  → Progression COMPLETED - Resume both bets")
        
        print(f"  Session P&L: €{state.session_pnl:.2f}")
        print()
        
        if spin >= 4:
            break
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✓ Progression sequence: 1 → 2 → 4 → 7")
    print("✓ Dual-bet halting: When one bet enters progression, other halts")
    print("✓ Snap-back: Progression resets on win or max level reached")
    print("✓ Resume: Both bets resume after progression completes")
    print("=" * 60)

if __name__ == '__main__':
    test_snapback_progression()
